#!/usr/bin/python
# -*- coding: utf-8 -*-

ct = {
    1: u'concept',
    2: u'coding',
    3: u'docs'
}

data = {
    u'Jakub Bubnicki': {
        'email': u'kbubnicki@ibs.bialowieza.pl',
        'contribution': [1,2,3]
    },
    u'Marcin Churski' : {
        'email': u'mchurski@ibs.bialowieza.pl',
        'contribution': [1,3]
    },
    u'Dries Kuijper': {
        'email': u'dkuijper@ibs.bialowieza.pl',
        'contribution': [1,3]
    },
    u'Leonardo Andrade': {
        'email': u'',
        'contribution': [1]
    },
    u'Krzysztof Nowak': {
        'email': u'',
        'contribution': [1,2]
    },
    u'Przemysław Kukulski': {
        'email': u'',
        'contribution': [2,3]
    },
    u'Piotr Tynecki': {
        'email': u'',
        'contribution': [2,3]
    },
    u'Łukasz Bołdys': { 
        'email': u'',
        'contribution': [2,3]
    },
    u'Łukasz Bołdys': {
        'email': u'',
        'contribution': [2,3]
    },
    u'Marek Supruniuk': {
        'email': u'',
        'contribution': [2,]
    }
}

if __name__ == '__main__':
    keys = data.keys()
    keys.sort(key=lambda x: x.split()[1])
    for key in keys:
        contribution = u','.join(
            [
                ct[k] for k in data[key]['contribution']
            ]
        )
        line = u'{contributor}; {email}; {ctype}'.format(
            contributor=key,
            email=data[key]['email'],
            ctype=contribution
        )
        print line
