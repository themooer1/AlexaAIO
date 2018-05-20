# A tool that formats AIO Episode names into a JSON fragment, which can be pasted into an Alexa Interaction Model

import AIO

episodeValue='{\n"id": null,\n"name": {"value": "EPHERE",\n"synonyms": []\n}\n},'

replacements={"1":"one","2":"two","3":"three","4":"four","5":"five","6":"six","7":"seven","8":"eight","9":"nine"}
fe=AIO.getFreeEpisodes()
re=AIO.getRadioEpisodes()
fnames=[i['Name'] for i in fe]
rnames=[i['Name'] for i in re]
for name in fnames:
    name=name.replace('.','').replace(',', '')
    for num,word in replacements.items():
        name=name.replace(num,word)
    print(episodeValue.replace("EPHERE",name))

for name in rnames:
    if name in fnames:
        pass
    else:
        name=name.replace('.','').replace(',', '')
        for num,word in replacements.items():
            name=name.replace(num,word)
    print(episodeValue.replace("EPHERE",name))