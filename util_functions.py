#Collection of misc functions needed to support essay_set.py and feature_extractor.py.
#Requires aspell to be installed and added to the path

aspell_path="aspell"
import re
import os
from sklearn.feature_extraction.text import CountVectorizer
import fisher
import numpy
from itertools import chain
import math
import nltk
import random
import pickle

def sub_chars(string):
    sub_pat=r"[^A-Za-z\.\?!,;:']"
    char_pat=r"\."
    com_pat=r","
    ques_pat=r"\?"
    excl_pat=r"!"
    sem_pat=r";"
    col_pat=r":"
    
    whitespace_pat=r"\s{1,}"
    whitespace_comp=re.compile(whitespace_pat)
    sub_comp=re.compile(sub_pat)
    char_comp=re.compile(char_pat)
    com_comp=re.compile(com_pat)
    ques_comp=re.compile(ques_pat)
    excl_comp=re.compile(excl_pat)
    sem_comp=re.compile(sem_pat)
    col_comp=re.compile(col_pat)
    
    nstring=sub_comp.sub(" ",string)
    nstring=char_comp.sub(" .",nstring)
    nstring=com_comp.sub(" ,",nstring)
    nstring=ques_comp.sub(" ?",nstring)
    nstring=excl_comp.sub(" !",nstring)
    nstring=sem_comp.sub(" ;",nstring)
    nstring=col_comp.sub(" :",nstring)
    
    nstring=whitespace_comp.sub(" ",nstring)
    return nstring
    
def spell_correct(string):
    f = open('tmpfile', 'w')
    f.write(string)
    f_path=os.path.abspath(f.name)
    f.close()
    p=os.popen(aspell_path + " -a < " + f_path + " --sug-mode=ultra")
    incorrect=p.readlines()
    p.close()
    incorrect_words=list()
    correct_spelling=list()
    for i in range(1,len(incorrect)):
        if(len(incorrect[i])>10):
            match=re.search(":",incorrect[i])
            if hasattr(match,"start"):
                begstring=incorrect[i][2:match.start()]
                begmatch=re.search(" ",begstring)
                begword=begstring[0:begmatch.start()]
                
                sugstring=incorrect[i][match.start()+2:]
                sugmatch=re.search(",",sugstring)
                if hasattr(sugmatch, "start"):
                    sug=sugstring[0:sugmatch.start()]
                
                    incorrect_words.append(begword)
                    correct_spelling.append(sug)
    newstring=string
    for i in range(0,len(incorrect_words)):
        sub_pat=r"\b" + incorrect_words[i] + r"\b"
        sub_comp=re.compile(sub_pat)
        newstring=re.sub(sub_comp,correct_spelling[i],newstring)
    return newstring
    
def ngrams(tokens, MIN_N, MAX_N):
    all_ngrams=list()
    n_tokens = len(tokens)
    for i in xrange(n_tokens):
        for j in xrange(i+MIN_N, min(n_tokens, i+MAX_N)+1):
            all_ngrams.append(" ".join(tokens[i:j]))
    return all_ngrams
    
def f7(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]
    
def count_list(the_list):
    count = the_list.count
    result = [(item, count(item)) for item in set(the_list)]
    result.sort()
    return result
    
def regenerate_good_tokens(string):
    toks=nltk.word_tokenize(string)
    pos_string=nltk.pos_tag(toks)
    pos_seq=[tag[1] for tag in pos_string]
    pos_ngrams=ngrams(pos_seq,2,4)
    sel_pos_ngrams=f7(pos_ngrams)
    return sel_pos_ngrams
    
def get_vocab(text,score,max_feats=750,min_length=100):
    dict = CountVectorizer(min_n=1,max_n=2,max_features=max_feats)
    dict_mat=dict.fit_transform(text)
    set_score=numpy.asarray(score,dtype=numpy.int)
    med_score=numpy.median(set_score)
    new_score=set_score
    if(med_score==0):
        med_score=1
    new_score[set_score<med_score]=0
    new_score[set_score>=med_score]=1
    
    fish_vals=[]
    for col_num in range(0,dict_mat.shape[1]):
        loop_vec=dict_mat.getcol(col_num).toarray()
        good_loop_vec=loop_vec[new_score==1]
        bad_loop_vec=loop_vec[new_score==0]
        good_loop_present=len(good_loop_vec[good_loop_vec>0])
        good_loop_missing=len(good_loop_vec[good_loop_vec==0])
        bad_loop_present=len(bad_loop_vec[bad_loop_vec>0])
        bad_loop_missing=len(bad_loop_vec[bad_loop_vec==0])
        fish_val=fisher.FishersExactTest.probability_of_table([[good_loop_present,bad_loop_present],[good_loop_missing,bad_loop_missing]])
        fish_vals.append(fish_val)
    
    cutoff=1
    if(len(fish_vals)>200):
        cutoff=sorted(fish_vals)[200]
    good_cols=numpy.asarray([num for num in range(0,dict_mat.shape[1]) if fish_vals[num]<=cutoff])

    getVar = lambda searchList, ind: [searchList[i] for i in ind]
    vocab=getVar(dict.get_feature_names(),good_cols)
        
    return vocab
    
    
def edit_distance(s1, s2):
    d = {}
    lenstr1 = len(s1)
    lenstr2 = len(s2)
    for i in xrange(-1,lenstr1+1):
        d[(i,-1)] = i+1
    for j in xrange(-1,lenstr2+1):
        d[(-1,j)] = j+1
 
    for i in xrange(lenstr1):
        for j in xrange(lenstr2):
            if s1[i] == s2[j]:
                cost = 0
            else:
                cost = 1
            d[(i,j)] = min(
                           d[(i-1,j)] + 1, # deletion
                           d[(i,j-1)] + 1, # insertion
                           d[(i-1,j-1)] + cost, # substitution
                          )
            if i and j and s1[i]==s2[j-1] and s1[i-1] == s2[j]:
                d[(i,j)] = min (d[(i,j)], d[i-2,j-2] + cost) # transposition
 
    return d[lenstr1-1,lenstr2-1]
    
class Error(Exception):
    pass
    
class InputError(Error):
    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg
        
        
def gen_cv_preds(clf,arr,sel_score,num_chunks=3):
    cv_len=int(math.floor(len(sel_score)/num_chunks))
    chunks=[]
    for i in range(0,num_chunks):
        range_min=i*cv_len
        range_max=((i+1)*cv_len)
        if i==num_chunks-1:
            range_max=len(sel_score)
        chunks.append(range(range_min,range_max))
    preds=[]
    set_score=numpy.asarray(sel_score,dtype=numpy.int)
    chunk_vec=numpy.asarray(range(0,len(chunks)))
    for i in range(0,len(chunks)):
        loop_inds=list(chain.from_iterable([chunks[int(z)] for z,m in enumerate(range(0,len(chunks))) if int(z)!=i ]))
        sim_fit=clf.fit(arr[loop_inds],set_score[loop_inds])
        preds.append(sim_fit.predict(arr[chunks[i]]))
    all_preds=numpy.concatenate((preds[0],preds[1],preds[2]),axis=0)
    return(all_preds)
    
def gen_model(clf,arr,sel_score,num_chunks=3):
    set_score=numpy.asarray(sel_score,dtype=numpy.int)
    sim_fit=clf.fit(arr,set_score)
    return(sim_fit)
    
def gen_preds(clf,arr,num_chunks=3):
    if(hasattr(clf,"predict_proba")):
        ret=clf.predict(arr)
        #pred_score=preds.argmax(1)+min(x._score)
    else:
        ret=clf.predict(arr)
    return ret
    
def calc_list_average(l):
    total = 0.0
    for value in l:
        total += value
    return total/len(l)
    
stdev=lambda d:(sum((x-1.*sum(d)/len(d))**2 for x in d)/(1.*(len(d)-1)))**.5

def quadratic_weighted_kappa(rater_a, rater_b, min_rating = None, max_rating = None):
    assert(len(rater_a) == len(rater_b))
    if min_rating is None:
        min_rating = min(rater_a + rater_b)
    if max_rating is None:
        max_rating = max(rater_a + rater_b)
    conf_mat = confusion_matrix(rater_a, rater_b,
                                     min_rating, max_rating)
    num_ratings = len(conf_mat)
    num_scored_items = float(len(rater_a))

    hist_rater_a = histogram(rater_a, min_rating, max_rating)
    hist_rater_b = histogram(rater_b, min_rating, max_rating)

    numerator = 0.0
    denominator = 0.0
    
    if(num_ratings>1):
        for i in range(num_ratings):
            for j in range(num_ratings):
                expected_count = (hist_rater_a[i] * hist_rater_b[j]
                                / num_scored_items)
                d = pow(i - j, 2.0) / pow(num_ratings - 1, 2.0)
                numerator += d * conf_mat[i][j] / num_scored_items
                denominator += d * expected_count / num_scored_items
    
        return 1.0 - numerator / denominator
    else:
        return 1.0
    
def confusion_matrix(rater_a, rater_b, min_rating=None, max_rating=None):
    assert(len(rater_a) == len(rater_b))
    if min_rating is None:
        min_rating = min(rater_a)
    if max_rating is None:
        max_rating = max(rater_a)
    num_ratings = int(max_rating - min_rating + 1)
    conf_mat = [[0 for i in range(num_ratings)]
                for j in range(num_ratings)]
    for a, b in zip(rater_a, rater_b):
        conf_mat[a - min_rating][b - min_rating] += 1
    return conf_mat

def histogram(ratings, min_rating=None, max_rating=None):
    if min_rating is None:
        min_rating = min(ratings)
    if max_rating is None:
        max_rating = max(ratings)
    num_ratings = int(max_rating - min_rating + 1)
    hist_ratings = [0 for x in range(num_ratings)]
    for r in ratings:
        hist_ratings[r - min_rating] += 1
    return hist_ratings

def get_wordnet_syns(word):
    synonyms = []
    regex = r"_"
    pat = re.compile( regex )
    synset = nltk.wordnet.wordnet.synsets(word)
    for ss in synset:
        for swords in ss.lemma_names:
            synonyms.append(pat.sub(" ",swords.lower()))
    synonyms=f7(synonyms)
    return synonyms
    
def get_separator_words(toks1):
    tab_toks1=nltk.FreqDist(word.lower() for word in toks1)
    if(os.path.isfile("essay_cor_tokens.p")):
        toks2=pickle.load(open('essay_cor_tokens.p', 'rb'))
    else:
        essay_corpus=open("essaycorpus.txt").read()
        essay_corpus=sub_chars(essay_corpus)
        toks2=nltk.FreqDist(word.lower() for word in nltk.word_tokenize(essay_corpus))
        pickle.dump(toks2, open('essay_cor_tokens.p', 'wb'))
    sep_words=[]
    for word in tab_toks1.keys():
        tok1_present=tab_toks1[word]
        if(tok1_present>2):
            tok1_total=tab_toks1._N
            tok2_present=toks2[word]
            tok2_total=toks2._N
            fish_val=fisher.FishersExactTest.probability_of_table([[tok1_present,tok2_present],[tok1_total,tok2_total]])
            if(fish_val<.001 and tok1_present/float(tok1_total) > (tok2_present/float(tok2_total))*2):
                sep_words.append(word)
    sep_words=[w for w in sep_words if not w in nltk.corpus.stopwords.words("english") and len(w)>5]
    return sep_words
    
def encode_plus(s):
    regex=r"\+"
    pat=re.compile(regex)
    return pat.sub("%2B",s)
    
def getMedian(numericValues):
    theValues = sorted(numericValues)
    
    if len(theValues) % 2 == 1:
        return theValues[(len(theValues)+1)/2-1]
    else:
        lower = theValues[len(theValues)/2-1]
        upper = theValues[len(theValues)/2]
    
        return (float(lower + upper)) / 2 