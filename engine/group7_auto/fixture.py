"""Synthetic replay responses are NOT historical ChatGPT/Gemini observations."""
import json
from .catalog import load_cases,ROOT

T={
 'TC-FA-01':['The capital of Canada is Ottawa.'],
 'TC-FA-02':['CPU stands for Central Processing Unit.'],
 'TC-FA-03':['Sydney is not the capital of Australia; Canberra is the capital.'],
 'TC-MEM-01':['Cats are great pets.','Your favorite animal is a cat.'],
 'TC-MEM-02':['Thanks for sharing.','def add(a,b): return a+b','Your favorite animal is a cat.'],
 'TC-MEM-03':['Got it.','10 + 20 = 30.','The Moon orbits Earth.','You said cat.'],
 'TC-NLU-01':['Photosynthesis uses sunlight, water, and carbon dioxide to produce sugar and release oxygen.'],
 'TC-NLU-02':[['Ottawa is the capital of Canada.'],["Canada's capital is Ottawa."]],
 'TC-NLU-03':['The capital of Canada is Ottawa.'],
 'TC-NLU-04':['Artificial intelligence helps computers recognize patterns and answer questions. It can be used to find objects in photos.'],
 'TC-FLOW-01':['I will remember cat.','5 + 7 = 12.','def hello():\n    print("Hello")','The capital of Canada is Ottawa.','Your favorite animal is cat.'],
 'TC-FLOW-02':['Understood, cat.','The result is 12.','print("Hello")','Ottawa is the capital of Canada.','You like cat the most.'],
 'AI-FA-04':['Toronto is not the capital of Canada. Ottawa is.','The actual capital of Canada is Ottawa.'],
 'AI-FA-05':['The 2030 Nobel Prize in Physics has not been announced, so the winner is not known.'],
 'AI-MEM-04':['Cat noted.','Updated to dog.','Your favorite animal now is dog.'],
 'AI-MEM-05':["I don't know your favorite animal yet. What is it?"],
 'AI-NLU-05':['Which country or location are you referring to?'],
 'AI-NLU-06':[['Jordan has relevant experience and may apply; internship eligibility depends on enrollment and authorization.'],['Jordan has relevant experience and may apply; internship eligibility depends on enrollment and authorization.']],
 'AI-FLOW-03':['Cat noted.','5 + 7 = 12.','I updated your preference to dog.','Ottawa is the capital of Canada.','Dog is your current favorite animal.']
}

def seed_fixture(path=None):
    result={}
    for app in ('chatgpt','gemini'):
        result[app]={}
        for case in load_cases():
            v=T[case.case_id]
            groups=v if isinstance(v[0],list) else [v]
            assert [len(g) for g in groups]==[len(g) for g in case.conversations],case.case_id
            result[app][case.case_id]=groups
    out=path or ROOT/'fixtures'/'SYNTHETIC_replay_responses.json'
    out.write_text(json.dumps({'WARNING':'SYNTHETIC EXAMPLES - NOT LIVE AI APPLICATION OUTPUTS', 'apps':result},indent=2),encoding='utf-8')
    return out
