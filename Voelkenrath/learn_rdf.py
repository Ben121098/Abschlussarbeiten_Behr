# Turning the certificate verification off 
# see: https://moreless.medium.com/how-to-fix-python-ssl-certificate-verify-failed-97772d9dd14c)
import os, ssl
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context



# from rdflib import Graph

# g = Graph()
# g.parse("http://dbpedia.org/resource/Georg_Wilhelm_Friedrich_Hegel")

# for index, (sub, pred,obj) in enumerate(g):
#     print(sub,'\n',pred,'\n', obj,'\n\n')
#     if index == 10:
#         break

# # print(g.serialize(format="ttl")


from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import FOAF, RDF
from rdflib import Namespace

g = Graph()
g.bind("foaf", FOAF)

bob = URIRef("http://example.org/people/Bob")
linda = BNode()  # a GUID is generated


n = Namespace("http://example.org/")
n.Person  # as attribute
# = rdflib.term.URIRef("http://example.org/Person")
n['first%20name']  # as item - for things that are not valid python identifiers
# = rdflib.term.URIRef("http://example.org/first%20name")




name = Literal("Bob")
age = Literal(24)

g.add((bob, RDF.type, FOAF.Person))
g.add((bob, n.name, name))
g.add((bob, n.age, age))
g.add((bob, n.knows, linda))
g.add((linda, RDF.type, n.Person))
g.add((linda, n.name, Literal("Linda")))
g.add((bob,n["Ethnicity"],Literal("European_people")))

print(g.serialize(format="ttl"))
