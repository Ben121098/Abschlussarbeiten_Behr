import spacy
from nltk.corpus import wordnet   

nlp = spacy.load("en_core_web_md")
doc = nlp("i am a former soldier")
doc0 = nlp("I have eaten an apple")
doc1 = nlp("This document captures the results collected from a broad survey of top-level ontologies, conducted by the IMF technical team.")
doc2 = nlp("Alex is going to travel to Canada")
doc3 = nlp("one apple cost 10 thousand $ in venesuela")
w = doc[0]
ww = doc[3]

# spacy.displacy.serve(doc3,style="dep")

#synset = wordnet.synsets("waste")
#for i in synset:
#    index = 0
#    for syn in i.lemmas():
#        index += 1
#        print(syn.name())
#        if index == len(i.lemmas()):
#            print("\n")
            
f = open(".\\pdfs2.txt","r")
string_big_text = f.read()
f.close()
big_text = nlp(string_big_text)
all_dep = []
all_dep0 = []
strange_string = "be rashly diminished” (Kant, 1964). Parsimony"
for tocken in big_text:
    if tocken.dep_ not in all_dep0:
        all_dep0.append(tocken.dep_)
    
    if 1==1:
        all_dep.append(tocken.dep_+"\t"+"from: "+tocken.text+"\t\t"+str(spacy.explain(str(tocken.dep_)))+"\t\t"+str(tocken.head))
        
print(len(all_dep0))


#ind = 0
#for i in big_text.sents:
#    ind += 1
#    print(i,"\n\n")
#    if ind>= 10:
#        break
    
lil = [k for k in big_text.sents] 
k = lil[-2]
for toc in k:
    print("{}\t{}\t{}\t{}\n".format(toc.lemma_,toc.dep_,spacy.explain(str(toc.dep_)),toc.head))

k = k.text
