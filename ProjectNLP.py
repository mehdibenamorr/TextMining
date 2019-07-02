# Query inputting

Text1=open("query.txt","r")
text=Text1.read()
query=text.split("\n")
q=18
print(query[q])
# Feature extracting/Syntaxic Tree

from pycorenlp import StanfordCoreNLP
nlp = StanfordCoreNLP('http://localhost:9000')
output = nlp.annotate(text, properties={
  'annotators': 'tokenize,ssplit,pos,depparse,parse,dcoref,ner',
  'outputFormat': 'json'
  })
syntaxic_output=[output['sentences'][i]['parse'] for i in range(0,len(output['sentences']))]


trimmed_output=[syntaxic_output[i].replace(" ","")  for i in range(0,len(syntaxic_output))]
trimmed_output=[trimmed_output[i].replace("(","")  for i in range(0,len(syntaxic_output))]
trimmed_output=[trimmed_output[i].replace(")"," ")  for i in range(0,len(syntaxic_output))]



# SRL: looking for possible params and functions (NP pos for parameters and VP for functions)

splitted_queries=[trimmed_output[i].split("\n") for i in range(0,len(trimmed_output))]
possible_funcs=[[splitted_queries[j][i] for i in range(0,len(splitted_queries[j])) if splitted_queries[j][i].find("VP")!=-1] for j in range(0,len(splitted_queries))]
possible_funcs=[[a[a.find("VP")+2:-2] for a in possible_funcs[i] ] for i in range(0,len(possible_funcs)) ]
possible_funcs=[[a.strip('`') for a in possible_funcs[i] ] for i in range(0,len(possible_funcs)) ]
possible_params=[[splitted_queries[j][i] for i in range(0,len(splitted_queries[j])) if splitted_queries[j][i].find("NP")!=-1] for j in range(0,len(splitted_queries))]
possible_params=[[a[a.find("NP")+2:-2] for a in possible_params[i] if a[a.find("NP")+2:-2]!="" ] for i in range(0,len(possible_params)) ]
possible_params=[[a.replace("`","") for a in possible_params[i] ] for i in range(0,len(possible_params)) ]
possible_params=[[a.replace("'","") for a in possible_params[i] ] for i in range(0,len(possible_params)) ]




def hasNumbers(inputString):
     return any(char.isdigit() for char in inputString)



tags=open("POS_TAGS.txt","r")
tags=tags.read()
tags=tags.split("\n")


for i in range(0, len(tags)):
    possible_params=[[a.replace(tags[i],"").strip() for a in possible_params[j] ] for j in range(0,len(possible_params))] 
    possible_funcs=[[a.replace(tags[i],"").strip() for a in possible_funcs[j] ] for j in range(0,len(possible_funcs))]

for i in range(0,len(possible_params)):
    if (possible_params[i][0]==output['sentences'][i]['tokens'][0]['lemma']):
        possible_funcs[i].extend([possible_params[i][0]])
        possible_params[i].remove(possible_params[i][0])    
    for j in range(0,len(possible_params[i])):
        if hasNumbers(possible_params[i][j]):
            a=possible_params[i][j].split()
            possible_params[i].remove(possible_params[i][j])
            possible_params[i]=a+possible_params[i]




# For SM later (only the possible parameters because we don't functions in parameters matching)
possible_parameters=[possible_params[i][:] for i in range(0,len(possible_params))] 




#Adding the possible function names if they are different then get
for i in range(0,len(possible_funcs)):
    if possible_funcs[i]!=[] :
        if possible_funcs[i][0]!='get':
            possible_params[i].append(possible_funcs[i][0]) 






# Loading the acktionKB (methods and their parameters)

import json
actionKB=json.loads(open("data/actionkb.json").read())
functions=[actionKB[i]["NAME"].replace("_"," ") for i in range(0,len(actionKB))]
functions_desc=[actionKB[i]["Desc"] for i in range(0,len(actionKB))]

parameter=[actionKB[i]["PARAMS"] for i in range(0,len(actionKB))]
#parameters=[[parameter[i][j]["Name"] for j in range(0,len(parameter[i]))] for i in range(0,len(parameter))]
parameters=[[parameter[i][j]["Desc"] for j in range(0,len(parameter[i]))] for i in range(0,len(parameter))] 

for i in range(0,len(functions)):
    if functions[i]!='get' :parameters[i].append(functions[i]) 
    parameters[i].append(functions_desc[i])



# Preparing the pair lists for the similarity computing using the word2vec model trained on wiki-2014 corpora

pairs_model='"pairs": [{\n        "t2": "dd",\n        "t1": "db"\n    }end'
add_on=', {\n        "t2": "dd",\n        "t1": "db"\n    }end'
pairs_list=[]
for k in range(0,len(parameters)):
    pairss=[]
    for i in range(0,len(possible_params[q])):
        pairs=pairs_model
        for j in range(0,len(parameters[k])):
            pairs=pairs.replace("db",possible_params[q][i])
            pairs=pairs.replace("dd",parameters[k][j])
            if j!=len(parameters[k])-1 :
                pairs=pairs.replace("end",add_on)
            else:
                pairs=pairs.replace("end","]\n}")
        pairss.append(pairs)
    pairs_list.append(pairss)



# Invoke the INDRA server for Similarity calculating (Word2Vec Model)

import http.client

conn = http.client.HTTPConnection("alphard.fim.uni-passau.de:8916",timeout=50)

headers = {
    'accept': "application/json",
    'content-type': "application/json",
    'authorization':  "Basic aW5kcmE6UVk4SDVkcm9ZODQ9",
    'cache-control': "no-cache"
}
values=[]
for i in range(0,len(pairs_list)):
    value=[]
    for j in range(0,len(pairs_list[i])):
        payload='{\n    "corpus": "wiki-2014",\n    "model": "W2V",\n    "language": "EN",\n    "scoreFunction": "COSINE",\n    '+pairs_list[i][j]+'\n'
        conn.request("POST", "/relatedness", payload, headers)
        res = conn.getresponse()
        data = res.read()
        evalued=json.loads(data.decode("utf-8"))
        value.append(evalued['pairs'])
    values.append(value)


# Calculating the score of each function with the query and sort them

scores=[]
for i in range(0,len(values)):
    s=0
    for j in range(0,len(values[i])):
        a=0
        for k in range(0,len(values[i][j])):
            a=a+values[i][j][k]['score']
        s=s+(a/len(values[i][j]))
    scores.append((functions[i],str(s/len(values[i])),i))

def getKey(item):
    return item[1]
scores=sorted(scores, key=getKey,reverse=True)


# Defining precision of function selection (varying Epsilon)
epsilon=0.08
Max=float(scores[0][1])
left=0
right=len(scores)
while(right-left>1):
    m=int((left+right)/2)
    if (Max-float(scores[m][1]))<epsilon :
        left=m
    else :
        right=m
candidates=scores[0:left+1]


# Semantic matching using our proposed processing ( NER-Similarity-Formatting)

from nltk.tag import StanfordNERTagger
from nltk.tokenize import word_tokenize

NER = StanfordNERTagger('stanford-ner-2016-10-31/classifiers/english.all.3class.caseless.distsim.crf.ser.gz','stanford-ner-2016-10-31/stanford-ner.jar',encoding='utf-8')

""" This in order to ignore the warnings"""
import warnings
warnings.filterwarnings('ignore')
    

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
def getcode(): # method that will return python code to execute
    global param
    global code
    code=[]
    for f in candidates:
        possible_parametersT=[possible_parameters[i][:] for i in range(0,len(possible_parameters))] 
        init_code=actionKB[f[2]]['instantiation']
        for i in range(0,len(actionKB[f[2]]['PARAMS'])):
            paramnotfound=True
            counter=0
            
            while (paramnotfound==True) and (counter<len(possible_parametersT[q])):
                counter+=1
                if ('NER' in actionKB[f[2]]['PARAMS'][i]):
                    #NER tagging
                    tag=actionKB[f[2]]['PARAMS'][i]['NER']
                    for j in range(0,len(possible_parametersT[q])):
                        token= word_tokenize(possible_parametersT[q][j])
                        tagged=[a[1] for a in NER.tag(token)]
                        if tag in tagged:
                            param=' '.join([token[h] for h in range(0,len(tagged)) if tagged[h]==tag])
                            paramnotfound=False
                            possible_parametersT[q].remove(possible_parametersT[q][j])
                            break
                else:
                    #similarity
                    param_scores=[]
                    for j in range(0,len(possible_parametersT[q])):
                        for a in values[f[2]][j]:
                            if a['t2']==actionKB[f[2]]['PARAMS'][i]['Desc']: param_scores.insert(-1,(a['score'],j))
                    param=possible_parametersT[q][sorted(param_scores,key=getKey,reverse=True)[0][1]]
                    try:
                        possible_parametersT[q].remove(param)
                    except: pass
                    paramnotfound=False
                if ('Format' in actionKB[f[2]]['PARAMS'][i]):
                    #Formatting
                    Format=actionKB[f[2]]['PARAMS'][i]['Format'].split(',')
                    if  Format[0]=='Number':
                        #assign number and check the preselected param
                        if is_number(param)==False:
                            for p in possible_parametersT[q]:
                                if is_number(p): 
                                    param=p
                                    break
                    elif Format[0]=="''":
                        param=query[q][query[q].find('"'):query[q].rfind('"')+1]
                    else:
                        DB=json.loads(open("data/"+actionKB[f[2]]['PARAMS'][i]['Data']).read())
                        check=False
                        for a in DB: 
                             if param in a.values():
                                check=True
                                break
                        if check==False:
                            paramnotfound=True
                            continue
                        elif param in [a[Format[0]] for a in DB]:
                            index=[a[Format[0]] for a in DB].index(param)
                            try:
                                possible_parametersT[q].remove(param)
                            except: pass
                            param=actionKB[f[2]]['PARAMS'][i]['Format'].replace(Format[0],param)
                        else:
                            for k in range(0,len(DB)):
                                if param in DB[k].values():
                                    index=k
                                    break
                            param=actionKB[f[2]]['PARAMS'][i]['Format'].replace(Format[0],DB[index][Format[0]])
                            try:
                                possible_parametersT[q].remove(param)
                            except: pass
                        if len(Format)>1:
                            for l in range(1,len(Format)):
                                param=param.replace(Format[l],DB[index][Format[l]])
            init_code=init_code.replace(actionKB[f[2]]['PARAMS'][i]['Name'],param)
        code.append(init_code)    
    return code



codes=getcode()
print(codes)

        
# Executing of the code
import sys
for i in range(0,len(codes)):
    print("Executing...",candidates[i][0])
    try:
        exec(codes[i])
    except:
        print("Something went wrong: "+str(sys.exc_info()[0]))
    
    









