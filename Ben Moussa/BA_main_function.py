import spacy
import rdflib
import os
import subprocess
import pandas as pd
import numpy as np
from rdflib.namespace import FOAF, RDF, RDFS
import pickle
import os
import transform_into_RDF
import libchebipy
from libchebipy import ChebiEntity



def get_tuples_from_noun_chunk(noun,tuples,call="main",Return=False):
    # Vorbereitung:
    invalide_adjs = ["-", "various", "several", "much", "many","very","same"]
    invalide_advs = ["-", "as", "several times", "several", "much","very", "many","same","samely"]
    determiners = ["all", "a", "an", "the", "some",#"and",
                   "several", "many", "much", "more", "-"]
    deleted = []
    if call == "main":
        noun_to_list = []
        for word in noun:
            if (word.text.lower() in determiners) or (
                    word.head.text.lower() in determiners):
                deleted.append(word.text.lower())
            else:
                noun_to_list.append(word)
        noun = noun_to_list
    if (noun[-1].pos_ in ["NOUN","PROPN"]) or (noun[-1].dep_ in ["pobj"] and noun[-1].pos_=="NUM"):
        head = noun[-1]
    else:
        return
    ind = 0
    mensioned = []
    adjectives = []
    adverbes = []
    conj_chunks = {}
    main_conj = []
    for word in reversed(noun):
        ind -= 1

        if word == head:
            compound = [head]
            continue        

        # Bearbeitung der compounds teilweise bestehend aus NOUNs:
        elif (word.pos_ in ["NOUN","PROPN"]) and (word.head == head) and (
                word.dep_ in ["compound","nmod","npavmod"]):
            new_chunk = []
            children = []
            nummod = head
            nummod_is_present = False
            for child in word.children:
                if child in noun:
                    children.append(child)
                if (child.dep_ == "nummod") and not (nummod_is_present):
                    nummod_is_present = True
                    nummod = child
            for word0 in reversed(noun[0:word.i]):
                if word0.pos_ == "PUNCT":
                    continue
                elif word0.dep_ == "nummod":
                    nummod = word0
                    nummod_is_present = True
                        
            if (word.dep_ == "nmod" and nummod_is_present):
                mensioned.append(word)
                subject_compound = ""
                object_compound = ""
                object_compound1 = ""
                word_achieved_in_compound = False
                for part in (noun[noun.index(nummod):]):
                    subject_compound += " "+ part.text.lower()
                    if not word_achieved_in_compound:
                        object_compound1 += " "+part.text.lower()
                    if word_achieved_in_compound:
                        object_compound += " "+part.text.lower()                        
                    if part == word:
                        word_achieved_in_compound = True

                tuples.add((subject_compound,RDFS.subClassOf,object_compound))
                tuples.add((subject_compound,"has value",object_compound1))
                tuples.add((object_compound,RDFS.subClassOf,"Numerical_Values"))
                tuples.append((subject_compound,RDFS.type,"Numerical_Value_With_Unit"))                
        # Komplexe COMPUNDs:
            if len(children) > 0:
                for part in noun:
                    if (part in list(word.lefts)):
                        new_chunk.append(part)
                new_chunk = new_chunk + [word]
                get_tuples_from_noun_chunk(new_chunk, tuples, call="sub")
                object_compound = ""
                subject_compound = ""
                for part in compound:
                    object_compound = part.text.lower() +" "+ object_compound
                for part in new_chunk:
                    subject_compound = subject_compound +" "+ part.text.lower() 
                
                subject_compound = subject_compound +" "+ object_compound
                tuples.add(( subject_compound, RDFS.subClassOf, object_compound ))
                tuples.add(( subject_compound,"related to",validate(subject_compound).replace(validate(object_compound),"") ))



            else:
                subject_compound = ""
                object_compound = ""
                for part in noun[ind:]:
                    subject_compound = subject_compound + " " + part.text.lower()
                    if part == noun[ind]:
                        continue
                    else:
                        object_compound = object_compound + " " + part.text.lower()
                tuples.add((subject_compound, RDFS.subClassOf, object_compound))
                tuples.add(( subject_compound,"related to",validate(subject_compound).replace(validate(object_compound),"") ))
                new_chunk = [word]
                mensioned.append(word)
                
                
                
        # CC- Erweiterung der NOUNs
            if (len(word.conjuncts) > 0) and (str(word.i) in list(conj_chunks.keys())):
                conj_chunks[str(main_conj.i)].append(new_chunk)
                hidden_chunks = []
                for chunk_list in conj_chunks[str(word.i)]:
                    hidden_chunks = hidden_chunks + chunk_list
                
                subject_compound = ""
                object_compound = ""
                for part in hidden_chunks:
                    subject_compound += " "+ part.text.lower()
                for part in reversed(compound):
                    object_compound += " "+ part.text.lower()
                    subject_compound += " "+ part.text.lower()
                tuples.add(( subject_compound, RDFS.subClassOf, object_compound ))
                for chunk_list in conj_chunks[str(word.i)]:
                    object_compound1 = ""
                    if chunk_list[0].pos_ not in ["CCONJ","PUNCT"]:
                        for element in chunk_list:
                            object_compound1 += " "+ element.text.lower()
                        object_compound1 += " "+ object_compound
                        tuples.add(( subject_compound, "related to",
                                       object_compound1))
                for part in reversed(hidden_chunks):
                    compound.append(part)
                        
                        
            else:
                for part in reversed(new_chunk):
                    compound.append(part)                
                
                
                
                
                
        # Berarbeitung der ADJECTIVES, der ADVERBES und der "npadvmod"s:
        elif ((word.pos_ == "ADJ" or word.dep_ == "amod") and (
              word.head == head) and (word.text.lower() not in 
              invalide_adjs)) or ((word.dep_ == "advmod") and (
              word.head in adjectives) and (word.text.lower() not in 
              invalide_advs)) or ((word.dep_ == "nummod") and (
              word.head == head)):# or (word.dep_=="nmod" and word.head==head):                            

            predicate = "has property"
            if word.dep_ == "nummod":
                predicate = "has number"
            npadvmod_list = []  
            for child in list(word.lefts):
                #if (child.pos_=="NOUN" and child.dep_=="npadvmod"):# or (
                        #child.pos_=="ADV" and child.dep_=="advmod"):
                if (child.dep_ in ["npadvmod","amod"]) or (word.dep_=="nummod" and child.dep_=="advmod"):
                    # or (child.dep_=="nummod"):        
                    npadvmod_list.append(child)
                    for child0 in list(word.lefts):
                        if (child0.pos_=="PUNCT") and (child0.i==child.i+1):
                            npadvmod_list.append(child0)
                    for grandchild in list(child.lefts):
                        npadvmod_list.insert(0,grandchild)

            npadvmod_list.append(word)
            object_compound = ""
            ontological_property = ""
            for part in npadvmod_list:
                ontological_property += part.text.lower() +" "
                
            for part in reversed(compound):
                object_compound += " {}".format(part)
            subject_compound = ontological_property + " " + object_compound

            tuples.add((subject_compound, RDFS.subClassOf, object_compound))
            tuples.add((subject_compound, predicate, ontological_property))
        
        
        # CC-Erweiterung der Adjektive und Adverbien:            
            if ((len(word.conjuncts)>0) and (str(word.i) in 
                list(conj_chunks.keys()))): 
                
                conj_chunks[str(main_conj.i)].append(npadvmod_list)
                hidden_chunks = []
                for adj_list in reversed(conj_chunks[str(main_conj.i)]):
                    hidden_chunks = hidden_chunks + adj_list
                subject_compound = ""
                object_compound = ""
                ontological_property = ""
                for part in hidden_chunks:
                    ontological_property += " "+ part.text.lower()
                    subject_compound += " "+ part.text.lower()
                for part in reversed(compound):
                    object_compound += " "+ part.text.lower()
                    subject_compound += " "+ part.text.lower()
                tuples.add(( subject_compound, RDFS.subClassOf,object_compound))
                tuples.add((subject_compound, "has property",ontological_property))
                
                for adj_list in conj_chunks[str(main_conj.i)]:
                    object_compound1 = ""
                    ontological_property = ""
                    if adj_list[0].pos_ not in ["CCONJ","PUNCT"]:
                        for element in adj_list:
                            ontological_property += " "+ element.text.lower()
                        object_compound1 = ontological_property +" "+ object_compound
                        tuples.add((subject_compound,RDFS.subClassOf,object_compound1))
                        tuples.add((subject_compound,"has property",ontological_property))
                
                for part in reversed(hidden_chunks):
                    compound.append(part)
                if word.pos_ == "ADJ" or word.dep_ == "amod":
                    adjectives.append(word)
                elif word.pos_ == "ADV":
                    adverbes.append(word)
            
            else:
                if word.pos_ == "ADJ" or word.dep_ == "amod":  
                    adjectives.append(word)
                    for part in reversed(npadvmod_list):
                        compound.append(part)
                elif (word.pos_ == "ADV"):# and (len(list(word.head.conjuncts))==0):
                    adverbes.append(word)
                    if len(list(word.head.conjuncts))==0:
                        for part in reversed(npadvmod_list):
                            compound.append(part)
                elif word.pos_ == "NUM" and word.dep_ == "nummod":
                    for part in reversed(npadvmod_list):
                        compound.append(part)
            
                
                
                

        # Bearbeitung der Conjuncts
        elif word.dep_=="conj":
            conj_children = []
            for part in noun:
                if part in list(word.lefts):
                    conj_children.append(part)
            new_chunk = conj_children + [word]
            subject_compound = ""
            object_compound = ""
            ontological_property = ""
            for part in new_chunk:
                subject_compound = subject_compound +" "+ part.text.lower()            
                ontological_property = ontological_property +" "+ part.text.lower()
            for part in reversed(compound):
                subject_compound = subject_compound +" "+ part.text.lower()
                object_compound = object_compound +" "+ part.text.lower()
            if len(conj_children) > 0:
                get_tuples_from_noun_chunk(new_chunk,tuples,call="sub")
            for conj in word.conjuncts:
                if conj.dep_ != "conj":
                    main_conj = conj
                    if str(main_conj.i) not in list(conj_chunks.keys()):
                        conj_chunks[str(main_conj.i)] = []
                    break

            if (main_conj.pos_ in ["NOUN","PROPN"]) and (main_conj.head == head) and (
                    main_conj.dep_ in ["compound","nmod"]):
                tuples.add(( subject_compound, RDFS.subClassOf, object_compound ))
                conj_chunks[str(main_conj.i)].append(new_chunk)
            # if the conj in an adjective or an adverb:            
            elif ((main_conj.pos_ == "ADJ" or main_conj.dep_ == "amod") and (
                    main_conj.head == head) and (main_conj.text.lower() 
                    not in invalide_adjs)) or ((main_conj.pos_ == "ADV") and (
              main_conj.head in adjectives) and (main_conj.text.lower() not in
                                           invalide_advs)):
                tuples.add(( subject_compound, RDFS.subClassOf, object_compound ))
                tuples.add(( subject_compound,"has property",ontological_property))
                conj_chunks[str(main_conj.i)].append(new_chunk)
                if word.pos_ == "ADJ" or word.dep_ == "amod":  
                    adjectives.append(word)
                elif word.pos_ == "ADV":
                    adverbes.append(word)
                
                
                
        # Bearbeitung der CCs und Punctuations               
        elif ((word.pos_ == "CCONJ") or (word.pos_ == "PUNCT" and
             len(list(word.head.conjuncts)) > 0)) :
            if (type(main_conj) == list) and (main_conj == []):
                compound.append(word)
            else:
                conj_chunks[str(main_conj.i)].append([word])
            
    if Return == True:
        relevant_noun_list = []
        for part in reversed(compound):
            relevant_noun_list.append(part)
        return relevant_noun_list    




""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"Parallelisierungsfunktionen"

def find_root_of_noun_list(noun_list):
    if (len(noun_list) == 0) or (type(noun_list) != list):
        return
    elif len(noun_list) == 1:
        return noun_list[0]    
    else:
        word = noun_list[0]
        head = word.head
        root_not_achieved = (head == word)
        i = 0
        while ((head in noun_list) and not (root_not_achieved)) and (i<500):
            i += 1
            word = head
            head = head.head
            root_not_achieved = (head == word)
    return word
            
        

# This function parallelize conjuncts in the same list
# input is a list of lists of tokens each representing a relevant "noun chunk"
# output is a list of lists of lists of tokens of chunk nouns, which are conjuncts
def parallelize_conjuncts(relevant_nouns):
    conj_chunks = {}
    integrated_noun_list = []
    uncomplete_integrated_noun_list = []
    added_conjs = []
    for noun in relevant_nouns:
        word = noun.copy()[-1]
        if ( word in added_conjs):
            continue
        elif (len(list(word.conjuncts)) > 0) :
            main_conj = word
            for conj in [word] + list(word.conjuncts):
                if conj.dep_ != "conj":
                    main_conj = conj
                    if str(main_conj.i) not in list(conj_chunks.keys()):
                        conj_chunks[str(main_conj.i)] = []
                    integrated_noun_list.append([])
                    break
            for conj in [main_conj] + list(main_conj.conjuncts):
                for noun0 in relevant_nouns:
                    if conj in noun0:
                        conj_chunks[str(main_conj.i)].append(noun0)
                        integrated_noun_list[-1].append(noun0)
                        added_conjs += noun0
        else:
            integrated_noun_list.append(noun)
            uncomplete_integrated_noun_list.append(noun)
    return conj_chunks, uncomplete_integrated_noun_list


# This function extraxts tuples from "of"-relations between "noun chunks":
def extract_tuples_from_prep(chunk,tuples = set()):
    preps = {"about":"about","above":"above","across":"across","per":"per","after":"after","against":"against",
         "along":"along","among":"among","around":"around","at":"at","before":"before",
         "behind":"behind","between":"between","beyond":"beyond","but":"in contrast to","by":"by",
         "concerning":"concerning","despite":"despite","down":"down","during":"during",
         "except":"except","following":"following","for":"for","from":"has origin","in":"in",
         "including":"including","into":"into","like":"similar to","near":"near","of":"related to","off":"off",
         "on":"on","onto":"onto","out":"out","over":"over","past":"past","plus":"plus",
         "since":"because of","throughout":"throughout","to":"to","towards":"towards","under":"under",
         "until":"until","up":"up","upon":"upon","up to":"up to","with":"in company of or including","due":"due to",
         "within":"within","without":"in absence of","as":"as","than":"than","because of":"because of","because":"because of"} 
    prep_indexes = [-1]
    for word in (chunk):
        if (word.dep_ == "prep") and (word.pos_ == "ADP"):
            prep_indexes.append(chunk.index(word))
    if len(prep_indexes) == 0:
        return
    iter_prep_indexes = iter(prep_indexes)
    prep_index = next(iter_prep_indexes)
    i = 0
    while (prep_index != prep_indexes[-1]) and (i<500):
        i += 1
        subject_compound = ""
        object_compound = ""
        object_compound2 = ""
        prep_index_next = next(iter_prep_indexes)
        for part in chunk[prep_index+1:]:
            subject_compound += " "+part.text.lower()
            if chunk.index(part) > prep_index_next:
                object_compound2 += " "+part.text.lower()
            if chunk.index(part) < prep_index_next:
                object_compound += " "+part.text.lower()        
        if object_compound != "":
            tuples.add((subject_compound,RDFS.subClassOf,object_compound))
        if object_compound2 != "":
            prep = chunk[prep_index_next]
            ontological_property = preps[prep.text]
            if (prep.text == "of"):
                prep_index_next_index = prep_indexes.index(prep_index_next)
                if prep_index_next == prep_indexes[-1]:
                    chunk_with_number = chunk[prep_index_next:]
                else:
                    prep_index_next_next = prep_indexes[prep_index_next_index+1]
                    chunk_with_number = chunk[prep_index_next: prep_index_next_next]
                for word0 in chunk_with_number :
                    if word0.pos_ == "NUM":
                        ontological_property = "has value"
                        break
            tuples.add((subject_compound, ontological_property ,object_compound2))
        prep_index = prep_index_next    




def separation_according_to_of(sent,reference_words):
    ofs = []
    related_words = {}
    for word in reference_words:
        for child in list(word.children):
            if child.dep_== "prep" and child.pos_ == "ADP":
                ofs.append(child)
                break
    if len(ofs) > 0:
        for of in ofs:
            related_words[str(of.i)] = []
            for word in sent[of.head.i:of.i+1]:
                if word in reference_words:
                    related_words[str(of.i)].append(word)
    return related_words

                

# This function uses the functions "extract_tuples_from_prep", "join_chunks" and 
# "parallelize_conjuncts" to create extract all of relations with respect
# to conjunctions and to respectively extract relevant tuples:
def parallelize_conjuncts_and_extract_tuples_from_of(sent,relevant_nouns,tuples):
    conj_chunks = parallelize_conjuncts(relevant_nouns)[0]
    keys = list(conj_chunks.keys())
    joining_results = join_chunks(relevant_nouns,tuples)[0]
    integrated_noun_list = joining_results.copy()
    chunks_with_conj = {}    
    for key in keys:
        conjs = conj_chunks[key]
        chunks_with_conj[key] = []
        main_conj = conjs[0][-1] 
        reference_words = [main_conj]
        reference_words = reference_words + list(main_conj.conjuncts)
        separation_results = separation_according_to_of(sent,reference_words)
        all_relatd_words = list(separation_results.values())
        mensioned_words = []
        for word_list in all_relatd_words:
            for word in word_list:
                mensioned_words.append(word)
        for word in reference_words:
            if word not in mensioned_words:
                all_relatd_words.append([word])

        for related_words in all_relatd_words:
            if related_words != []:
                main_word = related_words[0]
                chunk_with_conj = []
                for joined_chunk in joining_results:
                    if main_word in joined_chunk:
                        chunk_with_conj = joined_chunk.copy()
                        chunks_with_conj[key].append(chunk_with_conj.copy())
                        break
                for noun in relevant_nouns:
                    if main_word in noun:
                        relevant_noun = noun.copy()
                        break
                if (len(related_words) > 1) and not (chunk_with_conj == []):
                    inserting_index = chunk_with_conj.index(noun[0])
                    for part in relevant_noun:
                        if part in chunk_with_conj:
                            chunk_with_conj.remove(part)
                    for conj_word in related_words[1:]:
                        chunk_with_conj_copy = chunk_with_conj.copy()
                        for noun in relevant_nouns:
                            if conj_word in noun:
                                conj_word_noun = noun.copy()
                                break
                        for part in reversed(conj_word_noun):
                            chunk_with_conj_copy.insert(inserting_index,part)
                        chunks_with_conj[key].append(chunk_with_conj_copy.copy())
                        extract_tuples_from_prep(chunk_with_conj_copy,tuples)
                    
    if len(list(chunks_with_conj.values())) > 0:
        for integrated_noun in integrated_noun_list.copy():
            for conj_chunk_list in list(chunks_with_conj.values()):
                for conj_chunk in conj_chunk_list:
                    if all(item in conj_chunk for item in integrated_noun):
                        if integrated_noun in integrated_noun_list:
                            integrated_noun_list.remove(integrated_noun)
        
    return chunks_with_conj, integrated_noun_list


# Recursively determines all previous of-relations of a noun and 
# it is the noun related to
def join_chunk(chunks,chunk,tuples = set()):
    resulting_chunks = chunks.copy()
    all_chunks = []
    added_chunks = []
    if chunk in chunks:
        all_chunks.append(chunk)
        main_word = chunk[-1]
        first_prep_achieved = False
        for ans in (list(main_word.ancestors)):
            if (ans.pos_ == "ADP") and (ans.dep_ == "prep"):
                if not first_prep_achieved:
                    first_prep_achieved = True
                    of = ans
                    concerned_main_word = of.head
                    for chunk0 in chunks:
                        joined_chunk = []
                        if (concerned_main_word in chunk0) and (chunk0 != chunk):
                            joining_results = join_chunk(chunks[:chunks.index(chunk0)+1],chunk0)[0]
                            for result in joining_results:
                                if concerned_main_word in result:
                                    concerned_chunk = result
                                    concerned_main_word_index = concerned_chunk.index(concerned_main_word)
                                    joined_chunk = concerned_chunk[:concerned_main_word_index+1] +[of]+ chunk                        
                                    resulting_chunks.append(joined_chunk)
                                    extract_tuples_from_prep(joined_chunk,tuples)
                                    added_chunks = joined_chunk.copy()
                                    
                            for joined in [chunk0,chunk]:
                                if joined in resulting_chunks:
                                    resulting_chunks.remove(joined)
                            all_chunks.append(joined_chunk)
    return resulting_chunks, all_chunks, added_chunks


# Uses the function "join_chunk()" to determine all resulting of-chunks and
# and the resulting global chunks (joined_chunks) deleting nouns, wich are contained
# entirely in other joined ones: 
def join_chunks(relevant_nouns,tuples = set()):
    joined_chunks = relevant_nouns.copy()
    added_chunks = []
    for relevant_noun in relevant_nouns:
        added_chunk = join_chunk(relevant_nouns,relevant_noun)[2]
        if len(added_chunk) > 0:
            added_chunks.append(added_chunk)
    for added in added_chunks.copy():
        for compare_added in added_chunks.copy():
            if added != compare_added:
                if all(item in compare_added for item in added) and (
                        added in added_chunks):
                    added_chunks.remove(added)
                        
    for added in added_chunks:
        joined_chunks.append(added)
        extract_tuples_from_prep(added,tuples)
    for joined in joined_chunks.copy():
        for compare_joined in joined_chunks.copy():
            if compare_joined != joined:
                if all(item in compare_joined for item in joined) and (
                        joined in joined_chunks):
                    joined_chunks.remove(joined)
    return joined_chunks, added_chunks


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"Andere Funktionen"

# This function extracts the main "verb chunk" of the main sentence (ROOT):
def extract_verb_chunk(sentence,df,pos=-1):
    if pos == -1:
        pos = find_root_of_noun_list(sent)
        pos = pos.i
    sent = sentence.copy()
    for word in sent:
        if (word.dep_ == "conj") and ("VERB" in word.pos_):
            main_conj = list(word.conjuncts)[0]
            word.dep_ = main_conj.dep_ 
            word.head = main_conj.head
    verb_dependencies = ["relcl","advcl","ccomp","acl","ROOT"]
    other_dependencies = ["amod","npadvmod","advmod","pobj","compound","dobj","oprd","punct","aux","auxpass"]
    verb_chunks = []
    head_pos = df[pos].loc["head_position"]
        
    for word in reversed(sent):
        if ((word.dep_ in verb_dependencies+["xcomp","pcomp"]) or ("VB" in word.tag_ and 
                word.dep_ not in other_dependencies )) and (
                    df[word.i].loc["head_position"] == head_pos) and (word.text not in  ["of","to"]):
                    verb_chunks.append([sentence[word.i]])
                    if word.dep_ != "ROOT":
                        for word0 in reversed(sent[:word.i]):
                            if ((word0.is_ancestor(word)) and (word0.dep_ in 
                                verb_dependencies + ["xcomp","pcomp"])) and (
                                    df[word0.i].loc["head_position"] == head_pos) and (
                                            word0.text not in  ["of","to"]):                    
                                verb_chunks[-1].insert(0,sentence[word0.i])
    verb_chunks_results = verb_chunks.copy()

                
    # appending auxiliary to verbs
    verb_chunks_results = []
    for verb_chunk in verb_chunks:
        copied_verb_chunk = verb_chunk.copy()
        for verb in verb_chunk:
            verb_index = copied_verb_chunk.index(verb)
            children = list(sentence[verb.i].lefts)                    
                    
            aux_found = False
            for child in children:
                verb_index = copied_verb_chunk.index(verb)            
                if (child.dep_ in ["aux","auxpass"]) and (
                        df[child.i].loc["head_position"] == head_pos):
                    copied_verb_chunk.insert(verb_index,sentence[child.i])
                    aux_found = True
            if (not aux_found) and (len(list(verb.conjuncts)) > 0):
                children = []
                for conj in list(sentence[verb.i].conjuncts):
                    children += list(conj.lefts)
                for child in children:
                    verb_index = copied_verb_chunk.index(verb)
                    if (child.dep_ in ["aux","auxpass"]):
                        copied_verb_chunk.insert(verb_index,sentence[child.i])
                        
        verb_chunks_results.append(copied_verb_chunk)
    verb_chunks = verb_chunks_results
    
    # removing redundant or included verb chunks:
    to_remove = []
    for verb_chunk in verb_chunks:
        for copied_chunk in verb_chunks:
            if all(item in verb_chunk for item in copied_chunk) and (copied_chunk != verb_chunk):
                if copied_chunk in verb_chunks:
                    to_remove.append(copied_chunk)
    for chunk in to_remove:
        if chunk in verb_chunks:
            verb_chunks.remove(chunk)
            
    return verb_chunks



# This function visiualize the dependency graph according to SpaCy
def visualize(doc, style="dep"):
    html = spacy.displacy.render(doc,style=style)
    f = open(".\\Text_Files\\datavis.html","w")
    f.write(str(html))
    f.close()
    print("{}\\Text_Files".format(os.getcwd()))




# This function convertes the spacy doc variable into
# a pandas dataframe representation with all relevant token-informations
# It does as well differenciate between dependent and independent clauses
def doc_to_df(sent):
    sent_df = pd.DataFrame(index=["text", "dep", "tag", "pos", "direct_head", "direct_head_position",
                           "head_position", "root_verb"], columns=[a for a in range(len(sent))])
    root_pos = 0
    clauses = 0
    verb_pos = []
    verb_pos_all = []
    for i in sent_df.columns.values:
        sent_df[i].loc["text"] = sent[i].text
        sent_df[i].loc["tag"] = sent[i].tag_
        sent_df[i].loc["pos"] = sent[i].pos_
        sent_df[i].loc["dep"] = sent[i].dep_
        sent_df[i].loc["head_position"] = sent.to_json()["tokens"][i]["head"]
        sent_df[i].loc["direct_head_position"] = sent_df[i].loc["head_position"]
        sent_df[i].loc["direct_head"] = sent[sent.to_json()["tokens"][i]
                                             ["head"]].text
        sent_df[i].loc["root_verb"] = sent[i].head.text
        if (sent_df[i].loc["dep"] in ["relcl", "advcl", "ccomp", "acl"]) or (sent_df[i].loc["dep"] == "ROOT") or (
                (sent_df[i].loc["dep"] == "pcomp") and (sent_df[i].loc["tag"]=="VBG")) or (
                (sent_df[i].loc["dep"] == "xcomp") and (sent_df[sent_df[i].loc["direct_head_position"]].loc["dep"]=="acomp")):
            clauses += 1
            verb_pos.append(i)
            verb_pos_all.append(i)
            if sent_df[i].loc["dep"] == "ROOT": root_pos = i 

            
    for i in sent_df.columns.values:
        # j = sent_df[i].loc["head_position_position"]
        j = i
        max_iter = 0
        while (sent_df[j].loc["head_position"] not in verb_pos) and (max_iter<500):
            max_iter += 1
            j = sent_df[j].loc["head_position"]
        if not (j in verb_pos):
            j = sent_df[j].loc["head_position"]
        sent_df[i].loc["head_position"] = j
        sent_df[i].loc["root_verb"] = sent[j].text

    for i in verb_pos:
        sent_df[i].loc["head_position"] = i
        sent_df[i].loc["root_verb"] = sent[i].text
    if max_iter == 499:
        return False, False, False
    return sent_df, verb_pos, root_pos


                    

def set_predicat(sent, namespace, graph=rdflib.Graph):
    all_dep = {}
    for tock in sent:
        # if tock.dep_ not in list(all_dep.values()):
        if tock.dep_ in ["nsubj", "ROOT", "attr", "dobj","oprd"]:
            all_dep[str(tock.dep_)] = tock

    return all_dep




def text(noun_chunk,dic={}):
    spacy_dic = {}
    for key in dic:
        if not isinstance(key,(float,int)):
            spacy_dic[key] = dic[key]
        
    if type(noun_chunk) == spacy.tokens.token.Token:
        noun_chunk = [noun_chunk]
    noun_chunk_indexes = []   #[word.i for word in noun_chunk]
    for word in noun_chunk:
        if isinstance(word,(float,int)):
            noun_chunk_indexes.append(word)
        else:
            noun_chunk_indexes.append(word.i)
    for word in spacy_dic:
        if word.i in noun_chunk_indexes:
            substitution_word = noun_chunk[noun_chunk_indexes.index(word.i)]
            if substitution_word.text == word.text:
                noun_chunk = dic[word]
                break
    if type(noun_chunk) == str:
        return noun_chunk
    elif not isinstance(noun_chunk,(int,float)):
        if type(noun_chunk) == list:
            noun_chunk_text = [noun.text.lower() for noun in noun_chunk]
        else:
            noun_chunk_text = [noun_chunk.text.lower()]
        for ind, text in enumerate(noun_chunk_text):
            if "n't" in text :
                noun_chunk_text[ind] = "not"
        return " ".join(noun_chunk_text)
    return noun_chunk




def get_full_chunk(relevant_nouns,word,dic={},all_nouns=False):
    all_results = []
    if (word in dic) or (type(word)==list and any(item in list(dic.keys()) for item in word)):
        for key in dic:
            if (len(dic) > 0) and ((word==key) or (word.i==key.i and key.text.lower()==word.text.lower()) or ((type(word)==list) and  (key in word))):
                return [dic[key]]
                
    for relevant_noun in relevant_nouns:
        for part in relevant_noun :
            if (word.text == part.text) and (part.i == word.i) and (part.head.text == word.head.text):
                if all_nouns == False:
                    return relevant_noun
                elif all_nouns == True:
                    all_results.append(relevant_noun)
    if all_results != []:
        return all_results
    if type(word) != list:
        return [word]
    
def validate(string):
    if type(string) == str:
        while string[0] == " ":
            string = string[1:]
        while string[-1] == " ":
            string = string[:-1]
        string = string.replace("  "," ")        
        string = string.replace(",,,@","@")
        if string[-3:] == ",,,":
            string = string[:-3]
    elif string == RDFS.subClassOf:
        string = RDFS.subClassOf
    return string



def conjs(conj_chunks,noun_chunk,result="other",acomp="False"):
    conjs = []
    if type(noun_chunk) != list:
        noun_chunk = [noun_chunk]
    for key in list(conj_chunks.keys()):
        if noun_chunk in conj_chunks[key]:
            for conj_chunk in conj_chunks[key]:
                conjs.append(conj_chunk)
    if result == "other":
        conjs.remove(noun_chunk)
        return conjs
    elif result == "all":
        if noun_chunk not in conjs:
            conjs.append(noun_chunk)
        return conjs


def spec_to_append(spec0,all_nouns):
    spec_list = []
    if type(spec0) != list:
        spec = [spec0]
    spec = find_root_of_noun_list(spec0)
    all_specs = [spec] + list(spec.conjuncts)
    
    for sp in all_specs:
        for new_spec in get_full_chunk(all_nouns,sp,all_nouns=True):
            if type(new_spec) != list:
                spec_list.append([new_spec])
            else:
                spec_list.append(new_spec)
    return spec_list


def all_spec_from(spec,all_nouns,prep_type=False):
    all_spec = []
    if prep_type == False:
        for sp in spec:
            all_spec += spec_to_append(sp,all_nouns)
    else:
        for prep in spec:
            for prep1 in spec_to_append(prep[1],all_nouns):
                all_spec.append([prep[0],prep1])
    return all_spec
                

# Function for ordering the keys of all_verb_specifications so that complex_noun positiosn
    # are mentioned after ALL the corresponding nominal complex verbs (example sent65: species, used as a catalyst... and found in zeolites)
def ordered_keys(avs={}):
    if avs == {}:
        return []
    else:
        given_order = list(avs.keys())
        to_order = list(avs.keys())
        order_achieved = False
        counter = 0
        while (not order_achieved) and(counter<10):
            counter += 1
            order_achieved = True                        
            for pos in given_order:
                pos_i = to_order.index(pos)
                if "following_nominal_pos" in avs[pos]:
                    new_pos_i = pos_i
                    for to_be_followed in avs[pos]["following_nominal_pos"]:
                        new_pos_i = np.max((new_pos_i,to_order.index(to_be_followed)))
                    if new_pos_i != pos_i:
                        to_order.remove(pos)
                        to_order.insert(new_pos_i,pos)
                        order_achieved = False 
            given_order = to_order.copy()
        if counter == 10:
            print("maximal counter of {} is achieved !!!!".format(counter))
        return to_order    
            
def Filter(sent,symbs=-1):
    if isinstance(symbs,(float,int)):
        symbs = ["#","@","'",'"',"ç","^","+","\\","~","`","→"
                     "§","<",">","à","&","*","^","_",
                     "|","°","{","}","*","/","(",")","[","]","?"]
    verbial_dependencies = ["relcl","advcl","ccomp","acl","ROOT","xcomp"]
    all_deps = [tok.dep_ for tok in sent]
    str_sent = sent.text
    
    if sent.text.upper() == sent.text:
        raise Exception("Invalide sentence: titles or section name")
        
    tok_list = [tok for tok in sent]
    if len(tok_list) <= 1:
        raise Exception("Invalid sentence: sentence should contain 2 words at least")
    
    all_words_are_single_lettres = True
    num_of_sigle_lettre = 0
    for tok in tok_list:
        all_words_are_single_lettres = all_words_are_single_lettres and (len(tok.text)==1)
        if (len(tok.text)==1) and (tok.text not in ["I","a",",","'",'"']):
            num_of_sigle_lettre += 1
    if (all_words_are_single_lettres == True) or (num_of_sigle_lettre>=10):
        raise Exception("Invalid sentence: contains only single lettres or more than 5 of them")
    
    invalid_parts = ["see also",". . .","see image","see table","see figure","see drawing"]
    if any(part in sent.text.lower() for part in invalid_parts):
        raise Exception("Irrelevant sentence")
        
    if "ROOT" not in all_deps:
        raise Exception("No ROOT in the sentence")
    for tok in sent:
        if tok.dep_ == "ROOT" and (tok.pos_ == "NOUN" or "NN" in tok.tag_):
                raise Exception("sentence ROOT verb is a noun")
        if "VB" in tok.tag_ and tok.is_oov:
            raise Exception("The ROOT verb is out of vocabulary")
        if tok.dep_ in verbial_dependencies and "VB" not in tok.tag_:
            raise Exception("Non verb word: '{}' confused with a verb".format(tok))
    for symb in symbs:
        if symb in str_sent:
            raise Exception("The sentence:\n{}\ncontains the unknown symbols:\n{}".format(sent,symb))
    if "fig." in str_sent.lower():
        raise Exception("Figure description sentences are irrelevant")
        
    page_str = ["page ","pages ","fig. ","figure ","drawing ","table "]
    for p_str in page_str:
        if p_str in str_sent.lower():
            if str_sent[len(p_str)+str_sent.lower().find(p_str)].isnumeric():
                raise Exception("Unvalide sentence: contains page number or figure description")        
                
           



# Preprocessing sentences: eliminating parentheses, unwanted symbols and
# replacing unprocessable prepositions with processable ones
def actualise(sent_n,dic1):
    dic = {}
    for key in dic1:
        if isinstance(key,(float,int)):
            dic[key] = dic1[key]
        else:
            dic[sent_n[key.i]] = dic1[key]
    return dic

def preprocessing(sent,nlp=-1,replacement=False):
    
    # replacing unprocessable preps                
    if replacement == True:
        chebi_replacements = {}
        chebi_noun_replacements = {}
        unwanted_words = ["because of","by vertue of","thanks to","due to","in behalf of","for the sake of"]    
        not_yet_replaced = True
        counter = 0
        while (not_yet_replaced) and (counter<50):
            counter += 1
            not_yet_replaced = False
            for uw in unwanted_words:
                if uw in sent.text:
                    start_ind = sent.text.find(uw)
                    uw_nlp_list = [t for t in nlp(uw)]
                    for tok in sent:
                        if tok.idx == start_ind:
                            not_yet_replaced = True                            
                            replaced_i = tok.i
                            replaced_str = uw.lower().replace(" ","_")
                            replaced = nlp(replaced_str)[0]
                            uw_tok_list = [t for t in sent[replaced_i:replaced_i+len(uw_nlp_list)]]
                            new_sent = token_replace(sent,uw_tok_list[0],"since")
                            sent = nlp(new_sent)
                            chebi_replacements = actualise(sent,chebi_replacements)
                            chebi_noun_replacements = actualise(sent,chebi_noun_replacements)                            
                            for _ in range(1,len(uw_tok_list)):
                                uw_tok = sent[replaced_i+1]
                                new_sent = token_replace(sent,uw_tok,"")
                                sent = nlp(new_sent)
                                chebi_replacements = actualise(sent,chebi_replacements)
                                chebi_noun_replacements = actualise(sent,chebi_noun_replacements)
                                
                            chebi_replacements[tok.i] = replaced_str
                            chebi_replacements[sent[replaced_i]] = replaced_str
                            chebi_noun_replacements[sent[replaced_i]] = replaced
                            break
                    break            
            if counter >= 50:
                raise Exception("counter of replacement process exceeded maximal iteration number")
        return sent, chebi_replacements, chebi_noun_replacements
    
    
    # Eliminating parentheses and therir content
    parenths1 = ["(","[","{"]
    parenths2 = [")","]","}"]
    if not isinstance(sent,(str)):
        str_sent = sent.text
    else:
        str_sent = sent
    for ind, parenth1 in enumerate(parenths1):
        parenth2 = parenths2[ind]
        if (parenth1 in str_sent) and (parenth2 in str_sent) and (str_sent.count(parenth1) == str_sent.count(parenth2)):
            iter_counter = 0
            while ((parenth1 in str_sent) or (parenth2 in str_sent)) and (iter_counter<10):
                parenth1i = str_sent.find(parenth1)
                parenth2i = str_sent.find(parenth2)
                str_sent = str_sent[:parenth1i] + str_sent[parenth2i+1:]
                iter_counter += 1
            if iter_counter >= 50:
                raise "Max iterations in the function 'preprocessing' for the parenthesis {} is exceeded".format(parenth1)
    
    strings_to_replace = {"• ":"","•":"","  ":" ","-\n":"","\n":" ",", etc,":"","etc,":"","etc":"",", e.g.,":"","e.g.,":"","e.g.":"",", i.e.,":"",", i.e.":"","i.e.,":"","i.e.":"","ﬁ":"fi","’":"'","”":'"'}
    for unwanted_str in strings_to_replace:
        new_str = strings_to_replace[unwanted_str]
        iter_counter = 0
        while (unwanted_str in str_sent) and (iter_counter<50):
            iter_counter += 1
            str_sent = str_sent.replace(unwanted_str,new_str)
        if iter_counter >= 50:
            raise Exception("Max iterations in the function 'preprocessing' for the the preposition is exceeded")  
            
            
    if str_sent != "" and str_sent[0] in [" ",":","!"]:
        str_sent = str_sent[1:]
    if str_sent != "" and str_sent[-1] in [" ",":","!"]:
        str_sent = str_sent[:-1]
        
    return str_sent       
        
        
# Replaces a word (tok) in a sentence by another (substituting_word) to avoid
# oov's and replace them by chebi formula or explicite entity name
# The function replaces the tokens in the variable all_nouns as well
def token_replace(sent,tok,substituting_word):
    # substituting of tok in sent
    if type(sent) != list:
        str_sent = sent.text
        json = sent.to_json()["tokens"][tok.i]
        tok_start = json["start"]
        tok_end = json["end"]
        new_sent = str_sent[0:tok_start] + str(substituting_word) + str_sent[tok_end:]
        return new_sent
    # substituting of tok in all_noun
    else:
        all_nouns = sent
        if type(substituting_word) == str:
            nlp = spacy.load("en_core_web_md")
            substituting_word = nlp(substituting_word)[-1]
        new_nouns = []
        if not isinstance(tok,(float,int)):
            to_replace_i = tok.i
        for noun in all_nouns:
            new_noun = noun.copy()
            noun_tok_is = [t.i for t in noun]
            if to_replace_i in noun_tok_is:
                tok_ind = noun_tok_is.index(to_replace_i)
                new_noun[tok_ind] = substituting_word
            new_nouns.append(new_noun)
        return new_nouns
    
    
    
# get the ful complex acomp like in: "Nickel is 'smooth like butter' "    
def get_full_acomp(word,sent,df,tuples=[],dic={},appending=False):
    word = sent[word.i]
    pos = df[word.i].loc["head_position"]
    full_acomp = []
    for w in sent:
        if ((word.is_ancestor(w)) or (w==word)) and (df[w.i].loc["head_position"]==pos):
            full_acomp.append(w)
    full_acomp = [sent[i] for i in np.sort([tok.i for tok in full_acomp])]
    if appending == True:
        tuples.append( (text(full_acomp,dic),RDFS.subClassOf,text(word)) )
        tuples.append( (text(word),RDFS.subClassOf,"Semantic_Property") )
    return full_acomp    
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
"main function"

def tuples_from_text(sent,nlp=-1,show_graph=False,known_entities=[],formula_dic={},chebi_dic={},filter_on=True):
    sent = preprocessing(sent)
    if type(sent) == str:
        if nlp == -1:
            nlp = spacy.load("en_core_web_md")        
    sent = nlp(sent)
    
    if formula_dic == {}:
        formula_dic = pickle.load(open("formula_dic0.dat","rb"))
    if chebi_dic == {}:
        chebi_dic = pickle.load(open("chebi_dic0.dat","rb"))
        

    symbs = ["#",":",";","@","'",'"',"?","ç","^","+","-","\\","~",
                         "§","<",">","(",")","à","&","*",".",",","^","_","-",
                         "|","°","%","$","£","{","}","="";",":","*","/"]
            
    # Alignement with CHEBI:
    
    chebi_replacements = {}
    chebi_noun_replacements = {}
    new_tuples = []

        
    for tok in sent:
        if "NN" in tok.tag_:
            for ind in formula_dic:
                formula = formula_dic[ind]
                if ind in chebi_dic:
                    if (type(formula) == str) and (type(chebi_dic[ind])== str):
                        if (tok.text.lower() == formula.lower()) or (tok.text.lower() == chebi_dic[ind].lower()) or (tok.text.lower() == chebi_dic[ind].lower().replace(" atrom","")):
                            entity = ChebiEntity(str(ind))
                            entity_name = chebi_dic[str(ind)]
                            mass = str(entity.get_mass()) + " g pro mol"
                            charge = str(entity.get_charge()) + " e"
                            new_tuples.append(( entity_name,RDFS.subClassOf,"Chemical Entity" ))
                            new_tuples.append((entity_name,RDFS.subClassOf,"CHEBI_Chemical_Entity"))
                            new_tuples.append((entity_name,"has chebi identifier","CHEBI identifier "+ind))
                            new_tuples.append(("CHEBI identifier "+ind,RDFS.subClassOf,"CHEBI_identifier"))
                            new_tuples.append((entity_name,"has formula",formula))
                            new_tuples.append((formula,RDFS.subClassOf,"Chemical Formula"))
                            new_tuples.append((entity_name,"has molar mass",mass))
                            new_tuples.append((mass,RDFS.subClassOf,"Molar Mass"))
                            new_tuples.append((entity_name,"has charge",charge))
                            new_tuples.append((charge,RDFS.subClassOf,"Formal Charge"))
                            name_oov_list = [name_part.is_oov for name_part in nlp(entity_name)]
                            formula_oov_list = [formula_part.is_oov for formula_part in nlp(formula)]
                            name_oov = name_oov_list[0]
                            formula_oov = formula_oov_list[0]
                            for list_part in name_oov_list:
                                name_oov = name_oov or list_part
                            for list_part in formula_oov_list:
                                formula_oov = formula_oov or list_part
                            if nlp(tok.text)[0].is_oov == True:
                                if formula_oov == False:
                                    substitution_text = formula
                                    substituting_word = nlp(formula)[-1]
                                elif name_oov == False:
                                    substitution_text = entity_name
                                    substituting_word = nlp(entity_name)[-1]
                                else:
                                    substitution_text = "element"
                                    substituting_word = nlp("element")[-1]
                                sent = nlp(token_replace(sent,tok,substituting_word))
                                chebi_replacements[tok.i] = tok.text
                                chebi_replacements[sent[tok.i]] = tok.text
                                chebi_noun_replacements[sent[tok.i]] = tok
    
    
    
    
    
    
    
    
    # Überfürung der doc-Variablen in DataFrame-Variable zur Veranschaulichung 
    # der Haupt- und Nebensätze
    doc_to_df_results = doc_to_df(sent)
    df = doc_to_df_results[0]
    verb_positions = doc_to_df_results[1]
    root_pos = doc_to_df_results[2]

    
    
                    
    if isinstance(df,(bool)):
        return
    
    if filter_on == True:
        Filter(sent) 
    
    
    
    # Erstellung aller möglichen Tuples nur anhand der "noun chunks"
    # 1- Extraction der chunks
    only_nouns = [noun for noun in sent.noun_chunks]
    nouns = only_nouns.copy()
    entities = list(sent.ents)
    for ent in entities:
        included = False
        for noun in only_nouns:
            included = included and all(item in noun for item in ent)
        if  not included:
            nouns.append(ent)
            
    for noun in nouns:
        if noun.text.lower() in ["that", "which", "-","%"]:
            nouns.remove(noun)
    nouns_text = [noun.text for noun in nouns]
    
    # 2- Erstellung aller Tuples aus einem Satz:
    tuples = set()
    relevant_nouns = []
    for noun in (nouns):
        noun = get_tuples_from_noun_chunk(noun,tuples, call="main",Return = True)
        if noun is not None:
            relevant_nouns.append(noun)                        
    
    parallelizing_results = parallelize_conjuncts_and_extract_tuples_from_of(sent,relevant_nouns,tuples)
    conj_chunks = parallelizing_results[0]
    integrated_noun_list = parallelizing_results[1]
    verb_chunks = extract_verb_chunk(sent,df,0)
    all_nouns = integrated_noun_list
    for chunks in list(conj_chunks.values()):
        for chunk in chunks:
            all_nouns += [chunk]
    old_all_nouns = all_nouns.copy()        
    for key in chebi_noun_replacements.keys():
        value = chebi_noun_replacements[key]
        all_nouns = token_replace(all_nouns,key,value)
#    print(conj_chunks,"\n")
#    print(integrated_noun_list,"\n")
#    print(all_nouns,"\n")
        
    # print(verb_chunks)
    
    
                            
    
    preps_to_predicate = {"about":"about","above":"above","across":"across","after":"after","against":"against",
         "along":"along","among":"among","around":"around","at":"at","before":"before",
         "behind":"behind","between":"between","beyond":"beyond","but":"in contrast to","by":"by",
         "concerning":"concerning","despite":"despite","down":"down","during":"during",
         "except":"except","following":"following","for":"for","from":"has origin","in":"in",
         "including":"including","into":"into","like":"similar to","near":"near","of":"related to","off":"off",
         "on":"on","onto":"onto","out":"out","per":"per","over":"over","past":"past","plus":"plus",
         "since":"because of","because":"because of","throughout":"throughout","to":"to","towards":"towards","under":"under",
         "until":"until","up":"up","upon":"upon","up to":"up to","with":"in company of or including",
         "within":"within","without":"in absence of","as":"as","through":"through","than":"than","due":"due to"}    
    
    markers = ["after","while","if","as","even","though"
               ,"as if","because","even it","as soon as",
               "before","provided that","since","whereas",
               "unless","until","so that","once","for","rather",
               "in order that","rather than","although","on","at","how"]
    added_markers = ["on","at"]
    relative_pronouns = ["who","which","that","whose","whom",    "thereby","to"]
    relative_pronouns_to_predicate = {"who":"has subject","which":"has complement","that":"has complement","whose":"related to","whom":"has object","thereby":"thereby"}
    advmod = ['where', 'when', 'whenever']
    advmod_to_predicate = {"where":"in","when":"has specified time","whenever":"in"}
    marker_to_predicate = {"after":"after","while":"parallel in time","if":"has condition",
               "as":"has precondition","even":"even","though":"in contrast to"
               ,"as if":"similar to","because":"has reason",#"even it",
               "as soon as":"similtanuous to","before":"prior to",
               "provided that":"has conditiond","since":"has reason",
               "whereas":"in contrast to","unless":"refuted by","until":"ends with",
               "so that":"has purpose","once":"has condition","for":"has reason",
               "in order that":"has purpose","rather":"rather than","rather than":"rather",
               "although":"in contrast to","how":"how","at":"at","to":"to"}
    added_markers_to_predicate = {"on":"on","at":"at","to":"to"}
    introducer_to_predicate = marker_to_predicate.copy()
    introducer_to_predicate.update(relative_pronouns_to_predicate)
    introducer_to_predicate.update(advmod_to_predicate)
    introducer_to_predicate.update(added_markers_to_predicate)
    relative_clause_introducer = relative_pronouns + markers + advmod
    
    verb_relations = pd.DataFrame(columns=verb_positions,
                                  index=["verb_text","verb_dep","verb_i","related_to",
                                         "related_to_index","relation_type","relation","introducer","introducer_pos"])
    verbs = [sent[i] for i in verb_positions]
    corrected_verbs = {}
    for verb in verbs:
        corrected_verbs[verb] = verb.head
    for verb in verbs:
        if (verb.head.dep_ == "conj"):
            verbial_head = verb.head
            head_conj = list(verbial_head.conjuncts)[0] 
            if head_conj.i in verb_positions:
                corrected_verbs[verb] = head_conj
            
    verb_relations.loc["verb_i"] = verb_positions
    verb_relations.loc["verb_text"] = [verb.text for verb in verbs]
    verb_relations.loc["verb_dep"] = [verb.dep_ for verb in verbs]
    verb_relations.loc["related_to"] = [verb.head.text for verb in verbs]
    verb_relations.loc["related_to_index"] = [verb.head.i for verb in verbs ]
    verb_relations.loc["introducer"] = "none"
    verb_relations.loc["relation_type"] = [("ROOT"*(verb.dep_=="ROOT")+"nominal"*((verb.head.pos_=="NOUN") or (verb.head.dep_=="acomp"))
                        +"verbial"*(corrected_verbs[verb].i in verb_positions
                        and verb.dep_!="ROOT")) for verb in verbs ]
    
    dependent_clauses = {}
    for pos in verb_positions:
        clause = []
        for token in sent:
            if df[token.i].loc["head_position"] == pos:
                clause.append(token)
        dependent_clauses[pos] = clause.copy()
    
    # Determining the introducers                
    introducers = {}    
    introducers = {}    
    for clause_key in dependent_clauses:
        if clause_key != root_pos:
            dependent_clause = dependent_clauses[clause_key]    
            verb_index_in_clause = dependent_clause.index(sent[clause_key])
            for word in dependent_clause[:verb_index_in_clause]:  
                clause_word_index = dependent_clause.index(word)
                if (word.text.lower() in (advmod + relative_pronouns)) or (word.text.lower() in 
                    markers and (word.dep_ == "marker" or word.head == sent[clause_key]) ):
                    for sub_word in dependent_clause[clause_word_index:clause_word_index+1]:
                        key = df[sub_word.i].loc["head_position"]
                        if key not in list(introducers.keys()):
                            introducers[key] = []
                        else:
                            if introducers[key][-1].text.lower() in relative_pronouns:
                                break
                        introducers[key].append(sub_word)
                elif (sent[clause_key].head.dep_ == "acomp") and (sent[clause_key].head.i<-1+clause_key):
                    introducers[clause_key] = [intr for intr in sent[sent[clause_key].head.i+1:clause_key]]
                    
    for key in list(introducers.keys()):
        verb_relations[key].loc["introducer"] = [word.text.lower() for word in introducers[key]]
        verb_relations[key].loc["introducer_pos"] = introducers[key][-1].i
    
    introducer_values = list(introducers.values())
    for ind, value in enumerate(introducer_values):
        introducer_values[ind] = value[-1]
    
    # Initialising the dic variable for substituting complex nouns ans their
    # introducers with corresponding indexes
    dic = {}
    for key in introducers:
        if verb_relations[key].loc["relation_type"] == "nominal":
            dic[introducers[key][-1]] = sent[verb_relations[key].loc["related_to_index"]].i
            dic[sent[verb_relations[key].loc["related_to_index"]]] = sent[verb_relations[key].loc["related_to_index"]].i
    for p in verb_relations:
        if verb_relations[p].loc["relation_type"] == "nominal":
            complex_noun_i = verb_relations[p].loc["related_to_index"]
            dic[sent[complex_noun_i]] = complex_noun_i
    
            
    verb_dependencies = ["relcl","advcl","ccomp","acl","ROOT","xcomp","pcomp"]
    head_verb_dependencies = ["relcl","advcl","ccomp","acl","ROOT"]
    
    tt = []
    root_full_verbs = []
    
    for position in verb_positions:
        verb_chunks = extract_verb_chunk(sent,df,position)
    
    relation_type_list = list(verb_relations.loc["relation_type"])
    relation_type_list_cp = relation_type_list.copy()
    ordered_verb_positions = list(verb_relations.loc["relation_type"].index)
    ordered_verb_positions_cp = ordered_verb_positions.copy()
    verbial_positions = list(verb_relations.loc["relation_type"].index)
    
    verbial_positions_to_remove = []
    for pos in verbial_positions:
        if verb_relations[pos].loc["relation_type"] == "nominal":
            verbial_positions_to_remove.append(pos)
    
    for to_remove in verbial_positions_to_remove:
        verbial_positions.remove(to_remove)
            
    ordered_verbial_positions = []
    ind = 0
    verbial_order_done = False
    ROOT_appended = False
    reset = 0
    while (not verbial_order_done) and (reset<40):
        value = verbial_positions[ind]
        rel_type = verb_relations[value].loc["relation_type"]
        if rel_type == "ROOT" and not ROOT_appended:
            ordered_verbial_positions.append(value)
            ROOT_appended = True
        elif (df[verb_relations[value].loc["related_to_index"]].loc["head_position"] in ordered_verbial_positions) or (
                (verb_relations[value].loc["related_to_index"] in verb_relations) and (
                        verb_relations[verb_relations[value].loc["related_to_index"]].loc["relation_type"] == "nominal")) :            
            ordered_verbial_positions.append(value)
        verbial_order_done = all(item in ordered_verbial_positions for item in verbial_positions)
        if ind <= len(verbial_positions)-2:
            ind += 1
        else: 
            ind = 0
            reset += 1
    
    nominal_positions = []
    ordered_verb_positions = ordered_verbial_positions.copy()
    for pos in verb_positions.copy():
        if verb_relations[pos].loc["relation_type"] == "nominal":
            nominal_positions.append(pos)
            nominal_position =  verb_relations[pos].loc["related_to_index"]
            verbial_head = df[nominal_position].loc["head_position"]
            if verbial_head in ordered_verb_positions:
                insertion_index = ordered_verb_positions.index(verbial_head)+1
                ordered_verb_positions.insert(insertion_index,pos)
                

    all_preps = []
    all_adverbs = []
    all_attributes = []
    all_subjects = []
    all_indobjs = []
    all_dobjs = []
    all_acomps = []
    all_simple_acomps = []
    
    
    tt = []
    
    all_full_verbs = []
    all_verbs = []
    all_traited_verbs = []
    all_verb_specifications = {}
    all_verb_chunks = []
    complex_noun_index = []
    xcomp_verbs = []
    #ordered_verb_positions = [24]
    for position in ordered_verb_positions:
        if verb_relations[position].loc["relation_type"] in ["nominal","verbial","ROOT"]:
            verb_chunks = extract_verb_chunk(sent,df,position)
            all_verb_chunks.append(verb_chunks)
    
            # extract full verb
            for verb_chunk in (verb_chunks):
                related_full_verbs = []
                related_verbs = []
                previous_verbs = []
                full_verbs = []
                connection_full_verbs = []            
                for verb in verb_chunk:
                    if (verb.dep_ in verb_dependencies) or (verb.dep_ == "conj" and 
                       verb.head.dep_ in verb_dependencies):                    
                        full_verb = [verb]
                        subjects = []
                        preps = []
                        attributes = []
                        adverbs = []
                        indobjs = []
                        dobjs = []
                        acomps = []
                        simple_acomps = []
                        
                        append_tuple = True
                        # search for relevant children from the clause
                        verb_relevant_children = dependent_clauses[position].copy()
                        designation_relevant_children = verb_relevant_children.copy()
                        verb_children_to_remove = []
                        not_designation_relevant = []
                        for child in verb_relevant_children:
                            if ((child.head != verb ) and not (child.dep_=="conj" and list(child.conjuncts)[0].head==verb)):
                                verb_children_to_remove.append(child)
                                if child != verb:
                                    not_designation_relevant.append(child)
                                    
                        for nonrelevant_child in verb_children_to_remove:
                            if nonrelevant_child in verb_children_to_remove:
                                verb_relevant_children.remove(nonrelevant_child)
                        for nonrelevant_child in not_designation_relevant + introducer_values:
                            if nonrelevant_child in designation_relevant_children:
                                designation_relevant_children.remove(nonrelevant_child)
                        
                        # extracting the grammatical relations: subjects, direct object, ...
                        # extracting the full_verb
                        for verb_child in verb_relevant_children:
                            # Subject
                            if verb_child.dep_ in ["nsubj","nsubjpass","csubj"]:
                                subjects.append(get_full_chunk(all_nouns,verb_child))
                            # attributes
                            elif verb_child.dep_ in ["attr"]:
                                attributes.append(get_full_chunk(all_nouns,verb_child))
                            # adjectival complements
                            elif (verb_child.dep_ in ["acomp"]) or (verb_child.dep_=="conj"
                                 and list(verb_child.conjuncts)[0].dep_ in ["acomp"]):
                                acomps.append(get_full_acomp(verb_child,sent,df))
                                simple_acomps = [verb_child]
                            # full verb
                            elif verb_child.dep_ == "prt":
                                full_verb.append(verb_child)
                                full_verb = [sent[i] for i in np.sort([token.i for token in full_verb])]
                            elif verb_child.dep_ == "neg":
                                full_verb.append(verb_child)
                                full_verb = [sent[i] for i in np.sort([token.i for token in full_verb])]
                                
                            elif (verb_child.dep_ in ["aux","auxpass"]) and (verb_child.text != "to"
                            ) and (verb_child.text in [word.text for word in verb_chunk]):
                                full_verb.append(verb_child)
                                full_verb = [sent[i] for i in np.sort([token.i for token in full_verb])]                            
                                
                            # prepositions and corresponding noun chunks
                            elif verb_child.dep_ in ["prep","agent"]:
                                preps.append([[verb_child]])
                                prep = verb_child
                                if len(list(prep.rights)) > 0:
                                    for prep_child in list(prep.rights):
                                        if prep_child.pos_ in ["NOUN"]:
                                            break
                                    preps[-1].append(get_full_chunk(all_nouns,prep_child))
                                else:
                                    preps.remove(preps[-1])
                                    
                            # adverbes referring to the verb
                            elif verb_child.dep_ == "advmod":
                                adverbs.append([])
                                for word in list(verb_child.lefts)+[verb_child]:
                                    if word.dep_ in ["npadvmod","punct","advmod"]:
                                        adverbs[-1].append(word)
                            # direct objects of the verb            
                            elif verb_child.dep_ in ["dobj","oprd"]:
                                dobjs.append(get_full_chunk(all_nouns,verb_child))
                            # indirect object (dative)    
                            elif verb_child.dep_ == "dative":
                                indobjs.append(get_full_chunk(all_nouns,verb_child))
            
    
                        if verb.dep_ == "conj":
                            for head_verb_child in list(verb.head.children):
                                # subject relations of conj verbs
                                if head_verb_child.dep_ in ["nsubj","nsubjpass","csubj"]:
                                    subjects.append(get_full_chunk(all_nouns,head_verb_child))    
                                if (head_verb_child.i > verb.i) or (text(head_verb_child) in introducer_to_predicate):
                                    # attributes of conj verbs
                                    if head_verb_child.dep_ in ["attr"]:
                                        attributes.append(get_full_chunk(all_nouns,head_verb_child))
                                    # adjectival cpmlements for conj verbs
                                    elif (head_verb_child.dep_ in ["acomp"]) or (head_verb_child.dep_=="conj"
                                     and list(head_verb_child.conjuncts)[0].dep_ in ["acomp"]):
                                        acomps.append(get_full_acomp(head_verb_child,sent,df))
                                        simple_acomps = [head_verb_child]                                        
                                    # preposition to noun relations of conj verbs
                                    elif head_verb_child.dep_ in ["prep","agent"]:
                                        preps.append([[head_verb_child]])
                                        prep = head_verb_child
                                        if (head_verb_child.dep_ == "prep" and len(list(prep.rights)) > 0):
                                            for prep_child in list(prep.rights):
                                                if prep_child.pos_ in ["NOUN"]:
                                                    break
                                            preps[-1].append(get_full_chunk(all_nouns,prep_child))
                                        else:
                                            preps.remove(preps[-1])
                                    
                                    # advervs for conj verbs
                                    elif head_verb_child.dep_ == "advmod":
                                        adverbs.append([])
                                        for word in list(head_verb_child.lefts)+[head_verb_child]:
                                            if word.dep_ in ["npadvmod","punct","advmod"]:
                                                adverbs[-1].append(word)                          
                                    # direct objects of the conj erbs
                                    elif head_verb_child.dep_ in ["dobj","oprd"]:
                                        dobjs.append(get_full_chunk(all_nouns,head_verb_child))            
                                    # indirect object (dative) of the conj verbs
                                    elif head_verb_child.dep_ == "dative":
                                        indobjs.append(get_full_chunk(all_nouns,head_verb_child))
                        
                        if (verb.dep_ in head_verb_dependencies) or ( (len(list(verb.conjuncts))>0) and
                            (list(verb.conjuncts)[0].dep_ in head_verb_dependencies) ):
                            connection_full_verbs.append(full_verb)
                            
                            
                            
                        if (verb_relations[position].loc["relation_type"] in ["ROOT","verbial","nominal"]):
                            
                            verb_specifications = {}
                            for key in ["subject","attribute","direct_object","indirect_object","adverb","acomp","preps","following_verb_index"]:
                                verb_specifications[key] = []                        
                            verb_specifications["full_verb"] = full_verb 
                            verb_specifications["lemmatized_verb"] = [verb.lemma_]
                            if position in introducers and (verb_relations[position].loc["relation_type"] in ["ROOT","verbial"]):
                                verb_specifications["introducer"] = introducers[position]
                            for subject in subjects: verb_specifications["subject"] += spec_to_append(subject,all_nouns)
                            for attr in attributes: verb_specifications["attribute"] += spec_to_append(attr,all_nouns)
                            for adv in adverbs: verb_specifications["adverb"] = spec_to_append(adv,all_nouns)
                            for dobj in dobjs: verb_specifications["direct_object"] += spec_to_append(dobj,all_nouns)
                            for indobj in indobjs: verb_specifications["indirec_object"] += spec_to_append(indobj,all_nouns)
                            for acomp in acomps: verb_specifications["acomp"] += [acomp]
                            for prep in preps:
                                
                                # Checking if introducer is included in prep 
                                no_introducer_in = True
                                for part in prep:
                                    for subpart in part:
                                        if isinstance(subpart,(float,int)):# or (text(subpart).lower() in relative_pronouns):
                                            no_introducer_in = False            
                                            
                                # from prep=[[on],[catalytic surface]] to prep_connection=[on, catalytic, surface]
                                # repeat it with all corresponding nouns from spec_to_append()
                                for prep1 in spec_to_append(prep[1],all_nouns):
                                    prep_connection = []
                                    for subpart0 in prep[0]:
                                        prep_connection.append(subpart0) 
                                    for subpart1 in prep1:
                                        prep_connection.append(subpart1)
                                    verb_specifications["preps"].append(prep_connection.copy())
                                
                                
                            all_verb_specifications[verb.i] = verb_specifications.copy()
                                    
                            if (verb_relations[position].loc["relation_type"] in ["verbial","ROOT","nominal"]):
                                nominal = verb_relations[position].loc["relation_type"] == "nominal"
                                predicate = "has specification"
                                verb_dep = verb.dep_
                                introducer_reference_position = df[verb.i].loc["head_position"]
                                if verb.dep_ == "conj":
                                    main_clause_verb = list(verb.conjuncts)[0].head
                                    verb_dep = main_clause_verb.dep_
                                    main_clause_full_verb = get_full_chunk(all_full_verbs,main_clause_verb)
                                else:
                                    main_clause_verb = verb.head
                                    main_clause_full_verb = get_full_chunk(all_full_verbs,main_clause_verb)
                                
                                all_main_clause_verbs = [main_clause_verb] 
                                all_main_clause_full_verbs = [main_clause_full_verb] 
                                if len(list(main_clause_verb.conjuncts))>0 and main_clause_verb.dep_ != "conj":
                                    for v in list(main_clause_verb.conjuncts):
                                        all_main_clause_verbs.append(v)
                                        all_main_clause_full_verbs.append(get_full_chunk(all_full_verbs,v))
                                
                                if introducer_reference_position in introducers:
                                    introducer = introducers[introducer_reference_position][0]
                                    if introducer.dep_ in ["ccomp"]:
                                        predicate = "has complement or verb object"
                                    else:
                                        predicate = introducer_to_predicate[text(introducer)]
                                
                                for main_clause_v in all_main_clause_verbs:
                                    if (main_clause_v not in list(verb.conjuncts)) and (main_clause_v.i != verb.i):
                                        if verb_relations[position].loc["relation_type"] != "nominal":
                                            all_verb_specifications[main_clause_v.i]["following_verb_index"].append(verb.i)
                                            if verb.dep_ != "xcomp":
                                                tt.append( (main_clause_v.text,predicate,verb.text) )
                                                new_tuples.append( (main_clause_v.i,predicate,verb.i) )  
                                            
                                        
                            if (verb_relations[position].loc["related_to_index"] in verb_relations) and (verb_relations[verb_relations[position].loc["related_to_index"]].loc["relation_type"] == "nominal"):
                                nominal_verb_i = verb_relations[position].loc["related_to_index"]
                                n_verb = sent[nominal_verb_i]
                                if n_verb.dep_ == "conj":
                                    nominal_head = list(n_verb.conjuncts)[0].head
                                else:
                                    nominal_head = n_verb.head
                                if verb.i not in xcomp_verbs:
                                    all_verb_specifications[nominal_head.i]["following_verb_index"].append(verb.i)                                    
                                        
                                        
                                                         
                                        
                        if (verb_relations[position].loc["relation_type"] == "nominal"):
                            nominal_head = sent[verb_relations[position].loc["related_to_index"]]
                            complex_noun_index.append(nominal_head.i)
                            if nominal_head.i not in list(all_verb_specifications.keys()):
                                all_verb_specifications[nominal_head.i] = {}
                            if "following_nominal_pos" not in all_verb_specifications[nominal_head.i]:
                                all_verb_specifications[nominal_head.i]["following_nominal_pos"] = [verb.i]
                            else:
                                all_verb_specifications[nominal_head.i]["following_nominal_pos"].append(verb.i)
                            all_verb_specifications[nominal_head.i]["full_verb"] = full_verb.copy()
                            all_verb_specifications[nominal_head.i]["lemmatized_verb"] = [verb.lemma_]
                            all_verb_specifications[nominal_head.i]["full_noun"] = get_full_chunk(relevant_nouns,nominal_head)
                            if position in introducers:
                                all_verb_specifications[nominal_head.i]["introducer"] = introducers[position]
                                intro = introducers[position][-1]
                            for dict_key in ["subject","attribute","direct_object","indirect_object","adverb","acomp","preps","following_verb_index"]:
                                all_verb_specifications[nominal_head.i][dict_key] = []
                            for subject in subjects: 
                                all_verb_specifications[nominal_head.i]["subject"] += spec_to_append(subject,all_nouns)
                            for attr in attributes: 
                                all_verb_specifications[nominal_head.i]["attribute"] += spec_to_append(attr,all_nouns)
                            for adv in adverbs: 
                                all_verb_specifications[nominal_head.i]["adverb"] += spec_to_append(adv,all_nouns)
                            for dobj in dobjs: 
                                all_verb_specifications[nominal_head.i]["direct_object"] += spec_to_append(dobj,all_nouns)
                            for indobj in indobjs: 
                                all_verb_specifications[nominal_head.i]["indirect_object"] += spec_to_append(indobj,all_nouns)
                            for acomp in acomps: 
                                all_verb_specifications[nominal_head.i]["acomp"] += [acomp]
                            for prep in preps:
                                
                                for prep1 in spec_to_append(prep[1],all_nouns):
                                    prep_connection = []
                                    for subpart0 in prep[0]:
                                        prep_connection.append(subpart0) 
                                    for subpart1 in prep1:
                                        prep_connection.append(subpart1)
                                    all_verb_specifications[nominal_head.i]["preps"].append(prep_connection.copy())                            
                            if "introducer" not in all_verb_specifications[nominal_head.i]:
                                new_tuples.append(( nominal_head.i,"has complex specification",verb.i ))  
                            else:
                                if (all_verb_specifications[nominal_head.i]["introducer"][0].i > verb.i) or True:
                                    new_tuples.append((nominal_head.i,"has complex specification",verb.i))
                                        
    
                        
                        if append_tuple == True:
                            
                            subjects = all_spec_from(subjects,all_nouns)
                            attributes = all_spec_from(attributes,all_nouns)
                            acomps = all_spec_from(acomps,all_nouns)
                            preps = all_spec_from(preps,all_nouns,prep_type=True)
                            dobjs = all_spec_from(dobjs,all_nouns)
                            indobjs = all_spec_from(indobjs,all_nouns)
                            adverbs = all_spec_from(adverbs,all_nouns)
                            verb_relations_cp = verb_relations.drop(position,axis=1)                                       
                            if (verb.lemma_=="be") and (position not in list(verb_relations_cp.loc["related_to_index"])) and (
                                        verb.dep_ == "ROOT") and (preps == []) and (len(ordered_verb_positions)==1) and (
                                        "prt" not in [part.dep_ for part in full_verb]) and ("neg" not in [part.dep_ for part in full_verb]):
                                if (len(attributes) > 0) and (len(subjects) > 0):
                                    for attr in attributes:
                                        for conj_attr in conjs(conj_chunks,attr,result="all"):
                                            for subj in subjects:
                                                for conj_subj in conjs(conj_chunks,subj,result="all"):
                                                    new_tuples.append((text(conj_subj,dic),RDFS.subClassOf,text(conj_attr,dic)))
                                if (len(acomps) > 0) and (len(subjects) > 0):
                                    for acomp in acomps:
                                        for subj in subjects:
                                            for conj_subj in conjs(conj_chunks,subj,result="all"):
                                                new_tuples.append( (text(conj_subj,dic),"has property",text(acomp,dic)) )
                                            
                            else:                                
                                for subject in subjects:
                                    for conj_subj in conjs(conj_chunks,subject,result="all"):
                                        if verb.i == root_pos:
                                            new_tuples.append( (text(conj_subj,dic),"has complex property",verb.i) )
                                        else:
                                            new_tuples.append( (text(conj_subj,dic),"has complex specification",verb.i) )
                                            
                                for prep_connection in preps:
                                    if not any(item in prep_connection[-1] for item in list(dic.keys())) and (
                                            text(prep_connection[-1]) in [word.text for word in introducer_values]):
                                        continue
                                    else:
                                        new_tuples.append( (verb.i,preps_to_predicate[text(prep_connection[0],chebi_replacements)],text(prep_connection[-1],dic)) )
    
                                for adverb in adverbs:
                                    if not any(item in adverb for item in list(dic.keys())) and (
                                            text(adverb) in [word.text for word in introducer_values]):
                                        continue
                                    else:
                                        new_tuples.append( (verb.i,"has specification",text(adverb,dic)) )
                                        
                                for dobj in dobjs:
                                    if not any(item in dobj for item in list(dic.keys())) and (
                                            text(dobj) in [word.text for word in introducer_values]):
                                        new_tuples.append( (verb.i,introducer_to_predicate[text(dobj)],text(dobj,dic)) )
                                    else:
                                        for dobj_conj in conjs(conj_chunks,dobj,result="all"):
                                            new_tuples.append( (verb.i,"has direct object",text(dobj_conj,dic)) )
                                            
                                            
                                for indobj in indobjs:
                                    if not any(item in indobj for item in list(dic.keys())) and (
                                            text(indobj) in [word.text for word in introducer_values]):
                                        new_tuples.append( (verb.i,introducer_to_predicate[text(indobj)],text(indobj,dic)) )
                                    else:
                                        for indobj_conj in conjs(conj_chunks,indobj,result="all"):
                                            new_tuples.append( (verb.i,"has indirect object",text(indobj_conj,dic)) )
                                    
                                for acomp in acomps:
                                    for acomp_conj in conjs(conj_chunks,simple_acomps,result="all"):
                                        new_tuples.append((verb.i,"has adjectival complement",text(get_full_acomp(sent[acomp_conj[-1].i],sent,df,new_tuples,dic,appending=True),dic)))
                                            
                                            
                                if (related_full_verbs != []) and (verb.dep_ in ["xcomp"]):
                                    new_tuples.append( (related_verbs[-1].i,"has purpose or complement",verb.i ) )
                                    tt.append( (text(related_full_verbs[-1]),"has purpose or complement",text(full_verb) ))
                                    xcomp_verbs.append(verb.i)
                            
                            related_full_verbs.append(full_verb)
                            related_verbs.append(verb)
                            all_full_verbs.append(full_verb)
                            all_verbs.append(verb)
                            all_traited_verbs.append(verb)
                            previous_verbs.append(verb)
                                    
    
                        if position == root_pos:
                            root_full_verbs = connection_full_verbs.copy()
                            
                all_preps.append(preps)
                all_adverbs.append(adverbs)
                all_attributes.append(attributes)
                all_subjects.append(subjects)
                all_indobjs.append(indobjs)
                all_dobjs.append(dobjs)
                all_acomps.append(acomps)
    
    # extract the exact designation of the complex property containing 
    # the full verb with all the specifications:
    
    def avoiding_specification_repetetion(all_verb_specifications,xcomp_verbs=[],sent=-1):
        # Avoiding repeated specifications
        for key1 in all_verb_specifications.keys():
            for key2 in all_verb_specifications[key1].keys():
                old_list = all_verb_specifications[key1][key2].copy()
                clean_list = []
                for part in old_list:
                    if part not in clean_list:
                        clean_list.append(part)
                all_verb_specifications[key1][key2] = clean_list.copy()
                
        for key1 in all_verb_specifications:
            # Avoiding xcomp verb appending 
            if "full_noun" in all_verb_specifications[key1]:
                for verb_index in all_verb_specifications[key1]["following_verb_index"]:
                    if verb_index in xcomp_verbs:
                        all_verb_specifications[key1]["following_verb_index"].remove(verb_index)
            # Inserting "to" as introducer for xcomp verbs:
            else:
                if sent == -1:
                    verb = find_root_of_noun_list(all_verb_specifications[key1]["full_verb"])
                else:
                    verb = sent[key1]
                lefts = list(verb.lefts)
                for tok in lefts:
                    if key1 in xcomp_verbs:
                        if (tok.text.lower() == "to") and (tok.dep_ in ["aux"]):
                            to_tok = tok
                            all_verb_specifications[key1]["introducer"] = [to_tok]
                            break
                
        return all_verb_specifications
    
    
    # remove wrong appending of introducer words in other grammatical positions(adverb, subject, ...)
    # substitute complex nouns ("surface" in "surface on which the reaction takes place") by its index
    # so that it would be substituted by full complex property in concerning verb properties
    referring_introducers = ["who","whom","whose","what","that","which"]                    
    
    ordered_positions = ordered_keys(all_verb_specifications)
    
    
    relevant_keys = ["subject","attribute","direct_object","indirect_object","adverb","acomp","preps"]
    for key in all_verb_specifications:
        # Replacing introducers by their referred nouns according to dic or
        # removing them, when no accordation is there (how)
        intro_found = False
        if "introducer" in all_verb_specifications[key]:
            intro = all_verb_specifications[key]["introducer"][-1]
            intro_found = True
        elif (key in verb_relations) and (verb_relations[key].loc["relation_type"] == "nominal") and ("introducer" in
             all_verb_specifications[verb_relations[key].loc["related_to_index"]]):
            intro = all_verb_specifications[verb_relations[key].loc["related_to_index"]]["introducer"][-1]
            intro_found = True
        if intro_found:
            for sub_key in relevant_keys:
                for sub_part_ind,sub_part in enumerate(all_verb_specifications[key][sub_key]):
                    if (intro in set(sub_part)):
                        if (intro in dic) and (dic[intro] != key):   # and (dic[intro] not in [[],"",None]):
                            intro_ind = all_verb_specifications[key][sub_key][sub_part_ind].index(intro)
                            all_verb_specifications[key][sub_key][sub_part_ind][intro_ind] = dic[intro]
                        else:
                            all_verb_specifications[key][sub_key].remove(sub_part)
                            
            # replacing the complex noun by its sent index
            for sub_key in relevant_keys:            
                for index, sub_part in enumerate(all_verb_specifications[key][sub_key]):
                    sub_indexes = []
                    for token in sub_part:
                        if isinstance(token,(float,int)):
                            sub_indexes.append(token)
                        else:
                            sub_indexes.append(token.i)
                    for ind in complex_noun_index:
                        if ind in sub_indexes:
                            key_i = ordered_positions.index(key)
                            ind_i = ordered_positions.index(ind)
                            if key_i > ind_i:
                                ordered_positions.insert(key_i+1,ind)
                                ordered_positions.remove(ordered_positions[ind_i])
                            if sub_key != "preps":
                                all_verb_specifications[key][sub_key][index] = [ind]
                            elif sub_key == "preps":
                                pre = all_verb_specifications[key][sub_key][index][0]
                                all_verb_specifications[key][sub_key][index] = [pre,ind]
                                
    
    #print("\n",all_verb_specifications)
    # Extracting complex properties for each noun/verb only
    dic.update(chebi_replacements)
    all_verb_specifications = avoiding_specification_repetetion(all_verb_specifications,xcomp_verbs)
    complex_properties = {}
    keys_verbal = ["subject","attribute","direct_object","indirect_object","adverb","acomp","preps"]
    keys_nominal = ["full_verb","subject","attribute","direct_object","indirect_object","adverb","acomp","preps"]
    relevant_keys = ["subject","attribute","direct_object","indirect_object","adverb","acomp","preps"]
    for ind in reversed(list(all_verb_specifications.keys())):    
        
    # remove wrong appending of introducer words in other grammatical positions(adverb, subject, ...)
        if "introducer" in all_verb_specifications[ind]:
            if all_verb_specifications[ind]["introducer"][-1] in dic:
                intro = dic[all_verb_specifications[ind]["introducer"][-1]]
            else:
                intro = all_verb_specifications[ind]["introducer"][-1]
    
            for sub_key in relevant_keys:
                for sub_part in all_verb_specifications[ind][sub_key]:
                    if intro in set(sub_part): 
                        all_verb_specifications[ind][sub_key].remove(sub_part)
                        
    # substitute complex nouns ("surface" in "surface on which the reaction takes place") by its index
    # so that it would be substituted by full complex property in concerning verb properties                        
        for sub_key in relevant_keys:            
            for index, sub_part in enumerate(all_verb_specifications[ind][sub_key]):
                sub_indexes = []
                for token in sub_part:
                    if isinstance(token,(float,int)):
                        sub_indexes.append(token)
                    else:
                        sub_indexes.append(token.i)
                for cn_ind in complex_noun_index:
                    if cn_ind in sub_indexes:
                        if sub_key != "preps":
                            all_verb_specifications[ind][sub_key][index] = [cn_ind]
                        elif sub_key == "preps":
                            pre = all_verb_specifications[ind][sub_key][index][0:-1]
                            all_verb_specifications[ind][sub_key][index] = pre+[cn_ind]
                                
     
        complex_property_str = ""
        # traitment of complex nouns
        if "full_noun" in all_verb_specifications[ind]:
            keys = keys_nominal.copy()
            for key in keys:
                if all_verb_specifications[ind][key] != []:
                    complex_property_str += "@{}=".format(key)
                    if key == "full_verb":
                        complex_property_str += "{}".format(text(all_verb_specifications[ind]["full_verb"]))
                        continue
                    
                    for verb_spec in all_verb_specifications[ind][key]:
                        spec_str = ""
                        for spec_part in verb_spec:
                            if type(spec_part) == str:
                                spec_str += " "+spec_part
                            elif isinstance(spec_part,(float,int)): 
                                spec_str += " "+ dic[spec_part]                                
                            else:
                                spec_str += " "+text(spec_part,dic)
                        
                        complex_property_str += "{},,,".format(spec_str[1:])
                    if complex_property_str[-3:] == ",,,":
                        complex_property_str = complex_property_str[:-3]
            
            intro_part = ""
            if "introducer" in all_verb_specifications[ind]:
                intro = all_verb_specifications[ind]["introducer"][-1]
                preposition = all_verb_specifications[ind]["introducer"][:-1]
                if intro.text.lower() in ["which","that"]:
                    intro_part = "which"
                else:
                    intro_part = text([intro])
                intro_part = text(preposition) + intro_part
                if str(intro_part) in marker_to_predicate:                    
                    intro_part = marker_to_predicate[intro_part]
                    
                    
            complex_properties[ind] = text(all_verb_specifications[ind]["full_noun"],chebi_replacements)+":{}:".format(intro_part)+complex_property_str
            complex_properties[ind] = validate(complex_properties[ind])
            new_tuples.append( (complex_properties[ind], RDFS.subClassOf, text(all_verb_specifications[ind]["full_noun"],chebi_replacements)) )
        
        # traitment of complex verbs
        else:
            keys = keys_verbal.copy()
            for key in keys:
                if all_verb_specifications[ind][key] != []:
                    complex_property_str += "@{}=".format(key)
                    for verb_spec in all_verb_specifications[ind][key]:
                        spec_str = ""
                        for spec_part in verb_spec:
                            if type(spec_part) == str:
                                spec_str += " "+spec_part
                            elif isinstance(spec_part,(float,int)):
                                spec_str += " ["+ complex_properties[spec_part]+"]"
                            else:
                                spec_str += " "+text(spec_part,dic)
                        complex_property_str += "{},,,".format(spec_str[1:])
                    if complex_property_str[-3:] == ",,,":
                        complex_property_str = complex_property_str[:-3]
            intro_part = ""
            if "introducer" in all_verb_specifications[ind]:
                intro = all_verb_specifications[ind]["introducer"]
                intro_part = text(intro)
                if str(intro_part) in marker_to_predicate:
                    intro_part = marker_to_predicate[intro_part]
                    
            complex_properties[ind] = text(all_verb_specifications[ind]["full_verb"])+":{}:".format(intro_part)+complex_property_str
            complex_properties[ind] = validate(complex_properties[ind])
            new_tuples.append( (complex_properties[ind], RDFS.subClassOf ,text(all_verb_specifications[ind]["full_verb"])) )
            if text(all_verb_specifications[ind]["full_verb"]) != all_verb_specifications[ind]["lemmatized_verb"][0]:
                new_tuples.append( (text(all_verb_specifications[ind]["full_verb"]), RDFS.subClassOf , all_verb_specifications[ind]["lemmatized_verb"][0] ) )
            if ind == root_pos:
                new_tuples.append(( all_verb_specifications[ind]["lemmatized_verb"][0], RDFS.subClassOf, "Complex Semantic Property (verbs)" ))
            else:
                new_tuples.append(( all_verb_specifications[ind]["lemmatized_verb"][0], RDFS.subClassOf, "Complex Semantic Specification (verbs)" ))
    
    
        # Appending complex properties to each other
        if "following_verb_index" in all_verb_specifications[ind]:
            first_complex_specification_appended = False
            for following_i in all_verb_specifications[ind]["following_verb_index"]:
                ontological_object = complex_properties[ind]
                if not first_complex_specification_appended:
                    if complex_properties[ind][-2:] == "::":
                        complex_properties[ind] += "[{}]".format(complex_properties[following_i])
                    else:
                        complex_properties[ind] += "@[{}]".format(complex_properties[following_i])
                else:
                    complex_properties[ind] += "[{}]".format(complex_properties[following_i])
                first_complex_specification_appended =  True
                new_tuples.append( (complex_properties[ind],RDFS.subClassOf,ontological_object) )
                
    
    
                
    # Determine the literal complex specifications as string for each verb
    # appending to its string specification all concerning verb specifications
    def append_complex_specifications(all_verb_specifications,complex_properties,new_tuples=[]):
        # remove wrong appending of introducer words in other grammatical positions(adverb, subject, ...)
        relevant_keys = ["subject","attribute","direct_object","indirect_object","adverb","acomp","preps"]
        for key in all_verb_specifications:
            if "introducer" in all_verb_specifications[key]:
                intro = dic[all_verb_specifications[key]["introducer"][-1]]
                for sub_key in relevant_keys:
                    for sub_part in all_verb_specifications[key][sub_key]:
                        if intro in set(sub_part): 
                            all_verb_specifications[key][sub_key].remove(sub_part)
                            
        # substitute complex nouns ("surface" in "surface on which the reaction takes place") by its index
        # so that it would be substituted by full complex property in concerning verb properties                        
            for sub_key in relevant_keys:            
                for index, sub_part in enumerate(all_verb_specifications[key][sub_key]):
                    sub_indexes = []
                    for token in sub_part:
                        if isinstance(token,(float,int)):
                            sub_indexes.append(token)
                        else:
                            sub_indexes.append(token.i)
                    for ind in complex_noun_index:
                        if ind in sub_indexes:
                            if sub_key != "preps":
                                all_verb_specifications[key][sub_key][index] = [ind]
                            elif sub_key == "preps":
                                pre = all_verb_specifications[key][sub_key][index][0:-1]
                                all_verb_specifications[key][sub_key][index] = pre+[ind]
    
    
    
        # appending the respective complex property and substiution of complex noun indexes
        # by full property
        full_complex_properties = complex_properties
        for verb_i in reversed(list(all_verb_specifications.keys())):
            first_complex_specification_appended = False
            for following_i in all_verb_specifications[verb_i]["following_verb_index"]:
                ontological_object = full_complex_properties[verb_i]
                if not first_complex_specification_appended:
                    if full_complex_properties[verb_i][-2:] == "::":
                        full_complex_properties[verb_i] += "[{}]".format(complex_properties[following_i])
                    else:
                        full_complex_properties[verb_i] += "@[{}]".format(complex_properties[following_i])
                else:
                    full_complex_properties[verb_i] += "[{}]".format(complex_properties[following_i])
                first_complex_specification_appended =  True
                new_tuples.append( (full_complex_properties[verb_i],RDFS.subClassOf,ontological_object) )
                
        return full_complex_properties
    
    new_new_tuples = []
    
    #complex_properties = append_complex_specifications(all_verb_specifications,complex_properties,new_tuples)
    #complex_properties = full_complex_properties
    
    
    
    # Replacing the verb.i with the corresponding determined complex propery in the
    # extracted tuples of the variable new_tuples:
    for new_tuple in new_tuples:
        a = new_tuple[0]
        b = new_tuple[1]
        c = new_tuple[2]
        if isinstance(a, (int, float)) or isinstance(b, (int, float)) or isinstance(c, (int, float)):
            if isinstance(a, (int, float)):
                if a in complex_properties:
                    a_substituted = complex_properties[a]
                    a = a_substituted
                elif a in dic:
                    a = dic[a]
            if isinstance(b, (int, float)):
                if b in complex_properties:
                    b_substituted = complex_properties[b]
                    b = b_substituted
                elif b in dic:
                    b = dic[b]
            if isinstance(c, (int, float)):
                if c in complex_properties:
                    c_substituted = complex_properties[c]
                    c = c_substituted
                elif c in dic:
                    c = dic[c]
            new_tuple = (a,b,c)
        tuples.add(new_tuple)        
    
    tuples = list(tuples)
    pickle.dump(tuples, open("tuples.dat","wb"))
    pickle.dump(introducer_to_predicate,open("introducer_to_predicate.dat","wb"))
    
    
    if show_graph == True:
        transform_into_RDF.generate_protege_graph(tuples,show_graph=True)
    
    return tuples