#Extracts features from training set and test set essays

import numpy
import re
import nltk
import sys
from sklearn.feature_extraction.text import CountVectorizer
import pickle
import os
from itertools import chain

base_path = os.path.dirname(__file__)
sys.path.append(base_path)
from essay_set import essay_set
import util_functions


class feature_extractor:
    
    def __init__(self):
        self._good_pos_ngrams=self.get_good_pos_ngrams()
        self.dict_initialized=False
    
    def initialize_dictionaries(self,e_set):
        if(hasattr(e_set, '_type')):
            if(e_set._type=="train"):
                nvocab=util_functions.get_vocab(e_set._text,e_set._score)
                svocab=util_functions.get_vocab(e_set._clean_stem_text,e_set._score)
                self._normal_dict=CountVectorizer(min_n=1,max_n=2,vocabulary=nvocab)
                self._stem_dict=CountVectorizer(min_n=1,max_n=2,vocabulary=svocab)
                self.dict_initialized=True
                ret="ok"
            else:
                raise util_functions.InputError(e_set,"needs to be an essay set of the train type.")
        else:
            raise util_functions.InputError(e_set,"wrong input. need an essay set object")
        return ret
    
    def get_good_pos_ngrams(self):
        if(os.path.isfile("good_pos_ngrams.p")):
            good_pos_ngrams=pickle.load(open('good_pos_ngrams.p', 'rb'))
        else :
            essay_corpus=open("essaycorpus.txt").read()
            essay_corpus=util_functions.sub_chars(essay_corpus)
            good_pos_ngrams=util_functions.regenerate_good_tokens(essay_corpus)
            pickle.dump(good_pos_ngrams, open('good_pos_ngrams.p', 'wb'))
        return good_pos_ngrams
        
    def gen_length_feats(self,e_set):
        text=e_set._text
        lengths=[len(e) for e in text]
        word_counts=[len(t) for t in e_set._tokens]
        comma_count=[e.count(",") for e in text]
        ap_count=[e.count("'") for e in text]
        punc_count=[e.count(".")+e.count("?")+e.count("!") for e in text]
        chars_per_word=[lengths[m]/float(word_counts[m]) for m in xrange(0,len(text))]
        good_pos_tags=[]
        for i in xrange(0,len(text)) :
            pos_seq=[tag[1] for tag in e_set._pos[i]]
            pos_ngrams=util_functions.ngrams(pos_seq,2,4)
            overlap_ngrams=[i for i in pos_ngrams if i in self._good_pos_ngrams]
            good_pos_tags.append(len(overlap_ngrams))
        good_pos_tag_prop=[good_pos_tags[m]/float(word_counts[m]) for m in xrange(0,len(text))]
        
        length_arr=numpy.array((lengths,word_counts,comma_count,ap_count,punc_count,chars_per_word,good_pos_tags,good_pos_tag_prop)).transpose()
        
        return length_arr.copy()
    
    def gen_bag_feats(self,e_set):
        if(hasattr(self, '_stem_dict')):
             sfeats=self._stem_dict.transform(e_set._clean_stem_text)
             nfeats=self._normal_dict.transform(e_set._text)
             bag_feats=numpy.concatenate((sfeats.toarray(),nfeats.toarray()),axis=1)
        else:
            raise util_functions.InputError(self,"Dictionaries must be initialized prior to generating bag features.")
        return bag_feats.copy()
        
    def gen_feats(self,e_set):
        bag_feats=self.gen_bag_feats(e_set)
        length_feats=self.gen_length_feats(e_set)
        prompt_feats=self.gen_prompt_feats(e_set)
        overall_feats=numpy.concatenate((length_feats,prompt_feats,bag_feats),axis=1)
        overall_feats=overall_feats.copy()
        
        return overall_feats
        
    def gen_prompt_feats(self,e_set):
        prompt_toks=nltk.word_tokenize(e_set._prompt)
        expand_syns=[]
        for word in prompt_toks:
            synonyms=util_functions.get_wordnet_syns(word)
            expand_syns.append(synonyms)
        expand_syns=list(chain.from_iterable(expand_syns))
        prompt_overlap=[]
        prompt_overlap_prop=[]
        for j in e_set._tokens:
            prompt_overlap.append(len([i for i in j if i in prompt_toks]))
            prompt_overlap_prop.append(prompt_overlap[len(prompt_overlap)-1]/float(len(j)))
        expand_overlap=[]
        expand_overlap_prop=[]
        for j in e_set._tokens:
            expand_overlap.append(len([i for i in j if i in expand_syns]))
            expand_overlap_prop.append(expand_overlap[len(expand_overlap)-1]/float(len(j)))
            
        prompt_arr=numpy.array((prompt_overlap,prompt_overlap_prop,expand_overlap,expand_overlap_prop)).transpose()
        
        return prompt_arr.copy()