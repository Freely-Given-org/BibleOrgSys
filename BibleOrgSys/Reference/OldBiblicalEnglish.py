#!/usr/bin/env -S uv run
# -\*- coding: utf-8 -\*-
# SPDX-FileCopyrightText: © 2023 Robert Hunt <Freely.Given.org+BOS@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# OldBiblicalEnglish.py
#
# Module handling OpenBibleData Language functions
#
# Copyright (C) 2023-2026 Robert Hunt
# Author: Robert Hunt <Freely.Given.org+BOS@gmail.com>
# License: See gpl-3.0.txt
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Module handling Language functions.

moderniseEnglishWords( htmlStr:str, allowOptions:bool|None=False ) -> str
    Convert ancient English spellings to modern ones.
    May return something like 'endureth/endures' if allowOptions is set.
    This has been used for KJB-1769, KJB-1611, Biships Bible, Geneva Bible, Coverdale Bible,
        and middle-English Wycliffe Bible.
briefDemo() -> NonefullDemo() -> None
main calls fullDemo()


CHANGELOG:
    2025-03-20 Moved into BOS from OBD (OpenBibleData)
"""
import BibleOrgSys.BibleOrgSysGlobals as BibleOrgSysGlobals
from BibleOrgSys.BibleOrgSysGlobals import fnPrint, vPrint, dPrint


LAST_MODIFIED_DATE = '2026-08-25' # by RJH
SHORT_PROGRAM_NAME = "OldBiblicalEnglish"
PROGRAM_NAME = "OpenBibleData English Language Handling functions"
PROGRAM_VERSION = '0.99'
PROGRAM_NAME_VERSION = f'{SHORT_PROGRAM_NAME} v{PROGRAM_VERSION}'

DEBUGGING_THIS_MODULE = False


# Note that grave accents (`) will have already been removed from the Wycl text before this table is applied
ENGLISH_WORD_MAP = ( # Place longer words first,
                     #     use space before to prevent accidental partial-word matches
                     #     since we're only doing string matches (but they're case sensitive)
    # Fix typos
    ((' aud ',),' and '), # Cvdl Mrk 8:23, 10:50
    ((' thu s ',),' thus '), # Cvdl Isa 14:26
    # (('Joash’ s ','Joash’s ')), # UST Jdg 6:11
    (('mercyvpo ',),'mercy upon '), # Cvdl Mrk 10:48
    (('noman.But',),'no man. But'), # Cvdl Mrk 7:36
    (('plaged,preased',),'plagued, pressed'), # Cvdl Mrk 3:10
    (('symilitudes:How',),'similitudes: How'), # Cvdl Mrk 3:23

    # Pairs of words (two words to two words)
    #((' a boot',),' a boat'), # TOO GENERAL
    ((' afarre off',' afarre of',' a farre off',' a farre of'),' afar off'),
    ((' a flese ',),' a fleece '),((' a flees;',),' a fleece;'), # Psa 71:6, 72:6
    ((' a none ',),' anon '),
    ((' and grete ',),' and greet '), # Wycl Tob 5:11
    ((' an heare ',),' a hair '), # Gnva 1 Ki 1:52
    ((' an hors ',),' a horse '), # Wycl Tob 6:17
    ((' as flex',),' as flax'), # Wycl Isa 43:17
    ((' a summe.',),' a sum.'), # 1Ki 5:14
    (('at Euen,',),'at Evening,'),(('at euen ','at even ',),'at evening '),(('at euen,','at even,','at eue,'),'at evening,'),(('at euen.','at even.',),'at evening.'),(('at euen:','at even:',),'at evening:'),
        (('vntill Euen,','until even,','until euen,'),'until evening,'),(('vntyll euen.','vntill euen.','vntil euen.','vnto euen.'),'until evening.'),(('until euen:',),'until evening:'),
        (('unto even?','vnto euen?'),'until evening?'), # KJB Exo 18:14
        ((' was eue,',),' was evening,'), # Mrk 11:11
        ((' when Euen ',),' when evening '), # Mrk 6:47
        (('when euen ','when even '),'when evening '),
    (('a tokene,','a toke,'),'a token,'), # Cvdl Mrk 14:44
    ((' ben greete;',' ben grete;'),' been great;'), # Psa 110:2
    ((' be herd',),' be heard'), # Tob 4:1
    ((' bifor hem',),' before them'), # Wycl Mrk 9:1
    ((' blisside hem',),' blessed them'), # Wycl Mrk 10:16
    (('brede doutes',),'breed doubts'), # Cvdl/TNT 1Tim 1:4
    (('brokun meete',),'broken meat/food'), # Wycl Mrk 8:19
    (('carest for',),'care for/about'),
    (('comen hondes',),'common hands'), # TNT Mrk 7:2
    ((' daie yt ',),' day that '), # Cvdl 1 Sam 8:8
    (('dayly breede',),'daily bread'), # TNT Mat 6:11
    ((' deed men',),' dead men'), # Wycl Tob 1:20
    (('did prophecie',),'did prophesy'), # Acts 21:9
    (('doe prophecie',),'do prophesy'), # Jer 14:16
    ((' eate breede',' eate bredcare for/about',),' eat bread'), # Mrk 7:5
    ((' euer sens ',),' ever since '), # Psa 71:5
    (('floure of Lebanon',),'flower of Lebanon'),
    (('foule clothes','foule clothis'),'foul clothes'),
    (('foule spirite','foule spirit','foule sprete','fowle sprete'),'foul spirit'), # Mrk 5:8, 9:25
    (('fro God',),'from God'),
    (('gate him ',),'gat him '), # KJB-1611 2 Sam 17:23
    (('get bred',),'get bread'),
    (('have breade ',),'have bread '), # TNT Mrk 8:4
    (('hadden herd',),'had heard'),(('hath herd',),'hath heard'),(('haue herde',),'have heard'),(('was herd',),'was heard'),(('Y herde',),'I heard'), # 'herd' could be 'heard', but might be a 'herd'
    (('he grette ',),'he greeted '),(('and grette ',),'and greeted '), # Wycl Tob 5:6,11
    (('her heed,',),'her head,'), # Wycl Neh 4:4
    (('herd this',),'heard this'),
    (('herde that',),'heard that'),
    (('he seeth ',),'he seeeth '), # Psa 58:10
    (('hym, prophecie.',),'him, prophesy.'), # Mrk 14:65
    (('Hooli Goost',),'Holy Ghost'),
    ((' in breede',),' in breadth'), # Wycl Eze 45:1
    (('in counsels',),'in councils'), # Wycl Mrk 13:9
    ((' layed waiste',),' laid waste'), # Psa 79:7
    ((' laye sege ',),' lay siege '),
    ((' left hande',' lefthond'),' left hand'), # Sng 8:3
    (('loves have',),'loaves have'),
    ((' mightie hade',),' mighty hand'), # Cvdl
    ((' myne eare',' mine eare',' mine ear',' myn eere',),' my ear'), # Psa 48:5, 49:4
    ((' myn hond;',),' my hand;'), # Hos 2:10
    ((' no nother',),' no other'), # TNT Mrk 9:29
    ((' not herde',),' not heard'), # Rom 18:18
    #((' not y<sup>t</sup> ',),' not that '), # KJB-1611 Mrk 9:30
    (('nynthe our',),'ninth hour'),
    (('of breed','of bred'),'of bread'),
    (('of prophecie.',),'of prophecy.'), # Gnva Rev 19:10
    ((' righte hade',' right hade',' right honde',' riyt hond'),' right hand'),
    ((' preie for ',),' pray for '), # 1Cor 6:49 Note: In general, 'preie' could be 'pray' or 'prey'
    (('pruning hookes','pruninghooks'),'pruning-hooks'),
    (('schal moiste ',),'shall moisten '), # Joel 3:18
    (('sche felde ',),'she fell '),
    (('seelden hem;',),'sold them;'), # Joel 3:7
    ((' seyn hem,',),' seen them,'), # Wycl Mrk 10:14
    ((' shall doe;',),' shall do;'), # 2Ki 11:5
    ((' shall dye,',),' shall die,'),((' shal dye.',),' shall die.'), # Amo 6:9
    ((' shalt axe',),' shalt/shall ask'), # Mrk 6:23
    (('sheepe shearers','sheepeshearers','sheepshearers','sheepesherers'),'sheep-shearers'),
    ((' stale him ',),' stole him '), # 2Ki 11:2
    ((' sisters here ',),' sisters heere '), # KJB-1611 Mrk 6:3
    (('swete breed','swete bred'),'sweet bread'),
    (('summe the ',),'sum the '), # KJB-1611 2Ki 22:4
    (('swynes bloude','swynes blood','swines blood'),'swine’s blood'),(('swynes fleisch','swynes flesh','swines flesh'),'swine’s_flesh/prok'), # Isa 66:3,17
    ((' te cities',),' ten cities'), # Cvdl Mrk 7:31
    ((' that prophesie ',),' that prophecy '),((' that prophesie,',),' that prophesy,'), # Wycl Tob 2:6, Exe 13:2
    ((' the as ',),' thee/you as '), # Cvdl 1 Sam 8:8
    (('the heed ',),'the head '),
    (('the praye,',),'the prey,'), # KJB-1611 Eze 22:27
    (('the toke,',),'the token,'), # Cvdl Mrk 13:4
    ((' the ynne,',),' the inn,'),((' the ynne.',),' the inn.'), # Wycl Gen 24:32, Luk 2:7
    ((' thre ouris',),' three hours'), # Wycl Tob 12:22
    (('They breede ',),'They breed '), # Bshps Isa 59:5
    (('they prophecie',),'they prophesy'), # Jer 14:16
    (('to bye ',),'to buy '),
    (('to councels',),'to councils'), # KJB-1611 Mrk 13:9
    ((' to farre',),' too far'), # Hos 9:9
    ((' to hele ',),' to heal '), # Luk 4:18
    (('token his ',),'took his '),
    ((' to many:',),' too many:'), # Cvdl Jdg 7:4
    (('toke breede','took breed'),'took bread'),(('toke the bred',),'took the bread'), # Mrk 14:22 bred and breed don't show up as spelling mistakes
    (('to prophecie',),'to prophesy'), # Jer 14:16
    ((' to renne,',),' to run,'), # Wycl Tob 11:10
    (('the counsels',),'the councils'),(('the counsell ',),'the council '), # Mrk 13:9, 14:55
    ((' the heed.',),' the head.'), # Wycl Psa 109:7
    ((' the praye.',),' the prey.'), # Gnva Eze 19:3
    (('their pray.',),'their prey.'),(('their praye?','their pray?'),'their prey?'), # Hab 2:7
    (('the see ',),'the sea '),(('the see,',),'the sea,'),(('the see.',),'the sea.'),(('the see;',),'the sea;'), # Mrk 6:49
    ((' thin enem',),' thine enem'), # 1Sam 25:29
    (('thin hondis',),'thine hands'), (('Thin hond ',),'Thine hand '),(('thine hade ',),'thine hand '),(('thin hoond,','thine hade,'),'thine hand,'),(('thin hoond.',),'thine hand.'), # Psa 73:3, 145:16, Tob 13:2
    ((' thin heed',),' thine head'), # 1Ki 2:44
    (('this prophesy ','this prophecie '),'this prophecy '),(('this prophesie,','this prophesy,','this prophecie,'),'this prophecy,'), # Neh 6:12, Rev 22:19
        (('shall yet prophecie,',),'shall yet prophesy,'), # Zec 13:3
    ((' touche hem',),' touch them'), # Wycl Mrk 10:13
    (('vnleuended bred',),'unleavened bread'), # 2Chr 35:17
    ((' we axen',' we axe',),' we ask'), # Mrk 10:35
    (('we han ',),'we have '),
    (('wheate flowre',),'wheat flour'), # Psa 81:16
    (('whiche breede','which breede'),'which breed'), # Bshps/Gnva 1Tim 1:4
    (('Whos is ',),'Whose is '), # Wycl Mrk 12:16
    (('with greet',),'with great'),
    (('yonge me ',),'young men '),
    ((' youre heed.',),' your(pl) head.'), # Joel 3:7

    # Three words to three words
    (('Be ye war ',),'Be ye/you_all wary '),
    ((' claue the rockes',),' cracked the rocks'),(('cloaue the hard ',),'cracked the hard '),((' cloued the harde ',),' cracked the hard '), # Psa 78:15
    (('eate the bred ',),'eat the bread '), # Cvdl Psa 127:3
    (('fille the breede',),'fill the breadth'), # Wycl Isa 8:8
    (('for a pray ',),'for a prey '), # KJB-1611 Deu 3:7
    (('get the hense',),'get thee hence'), # Mrk 2:11
    (('in the breede',),'in the breadth'), # Wycl Jdt 1:2
    (('is a thurste',),'is athirst'), # Psa 42:1
    (('prouysion off bred',),'provision of bread'), # Ecc 5:16
    (('should neiye to',),'should approach to'), # Eze 44:15
    (('Slaye the not,',),'Slay them not,'), # Psa 59:11
    (('the breede therof ',),'the breadth thereof '), # Wycl Zec 5:2
    (('the mean time','the meene tyme'),'the meantime'), # Num 20:14
    (('them <span class="add_KJB-1611">that</span> prophecie',),'them <span class="add_KJB-1611">that</span> prophesy'),
        (('them that prophecie',),'them that prophesy'),
    (('vntyll ye euen.','vntyll the euen.','vntill the euen.','vntil the euen.','vnto the euen.'),'until the evening.'),(('vntyll the euen:','vntil the euen:','vnto the euen:','vntill ye euen:'),'until the evening:'), # Gnva Lev 17:15
    (('when the Euen ',),'when the Evening '),(('when the euen ','when the even '),'when the evening '),

    # Four words to four words
    (('booth winde and see ',),'both wind and sea '), # TNT Mrk 4:41
    (('in to a boot',),'into a boat'), # Wycl Mrk 8:13
    (('let the damme go','let the dam go'),'let the dam/female go'), # Deu 22:7
    (('saye vnto the, aryse,',),'say unto thee, arise,'),(('saye vnto the aryse',),'say unto thee arise'), # Mrk 2:11
    (('which is the breede',),'which is the breadth'), # Wycl Eph 3:18

    # Five words to four words
    (('go in to thin hous.',),'go into thine/your house.'), # Mrk 2:11
    (('out of This be which',),'out of Thisbe which'), # Tob 1:2
    (('writun on the breede of',),'written on the breadth of'), # Wycl Jer 17:1

    # Two words into one word
    ((' adoo ',),' ado '),((' a doo,',' adoe,',' adoo,'),' ado,'),((' adoo:',),' ado:'), # Mrk 5:39
    ((' a fer,',),' afar,'), # Wycl Tob 11:6
    ((' a foote ',' a foot ',' afoote ',' afote '),' afoot '), # Mrk 6:33
    (('a fore honde','afore hand','aforehande'),'aforehand'),
    (('aforetime','afore time'),'aforetime/previously'), # Dan 6:10
    ((' a go,',' agoo,',' agoe,'),' ago,'),((' agoe',' agoo'),' ago'),#((' agoo:',),' ago:'), # Bshps 2Ki 19:25, Cvdl Lam 2:!7
    ((' a loofe ',),' aloof '), # Psa 38:11
    ((' a nother ',),' another '), # TNT Mrk 9:10
    ((' a piece',),' apiece'), # KJB-1611 1Ki 7:15
    ((' asunder',' a sunder',' in sunder',' in sonder',' asundre',' asonder',' insunder'),' asunder/apart'), # Amos 6:11, Psa 46:9
    ((' all wayes',' allwayes',' alwayes',' alwaies',),' always'),
    ((' a mong ',),' among '), # Bshps Deu 2:14
    ((' an other',' anothir'),' another'),
    ((' any more',' enymore'),' anymore'), # Psa 74:10, Amos 8:2
    ((' any thyng',' eny thinge',' eny thige',' any thing'),' anything'),
    ((' a wei ',),' away '),
    (('Baal Peor',),'Baal-Peor'),(('Baalpeor',),'Baal-peor'), # Hos 9:10
    ((' backe sliding',),' backsliding'), # Hos 4:16
    ((' before hand ',),' beforehand '),
    (('Ben Iamin ','Be Iamin '),'Benyamin '), # Cvdl Psa 80:2
    ((' birth daye',' byrth daye',' birth day',' birthdai'),' birthday'), # Mrk 6:21
    (('breast plate','breastplate','brestplate','brestlap'),'breast-plate'),
    (('bryde grome','bridegroome','bridegrome','brydegrome','brydgrome','bridegrom'),'bridegroom'), (('Bridegrome',),'Bridegroom'),
    (('burnt offeringe','burnt offering','burnt offring','brentofferinge','brentofferynge','burntofferynge','burntofferinge','burntoffringe','burntoffrynge','burntoffering'),'burnt-offering'),
    (('brent sacrifice','brent sacrifici','burntsacrifice'),'burnt-sacrifice'),
    (('cankerworm ','canker worme ','cankerworme ','canker-worme '),'cankerworm/caterpillar '),(('cankerworm,','canker worme,','cankerworme,'),'cankerworm/caterpillar,'),(('cankerworm:','cankerworme:'),'cankerworm/caterpillar:'), # Joel 2:25
    ((' can not ',),' cannot '),
    ((' common wealth ',' comen welth '),' commonwealth '), # Eph 2:12
    ((' cornefelde',),' corn-field'), # Deu 23:25
    (('corne floores','cornefloores','cornflooris'),'corn-floors/storage-barns'),(('corne floore','corn floor','cornefloore','cornfloor'),'corn-floor/storage-barn'), # Hos 9:1
    ((' court yard',),' courtyard'), # Tob 2:9
    ((' crosse wayes',' crosse ways',' crossways'),' cross-roads'),((' crosse way',' crossway'),' cross-road'),
    ((' cup bearer',' cupbearer'),' cup-bearer'),
    ((' daye tyme',' day time'),' daytime'),
    ((' doore keeper',' doore keper',' door keeper',' doorkeeper',' dorekeper'),' door-keeper'), # Psa 84:10
    (('door posts','doore_posts'),'door-posts'), # Eze 41:16
    (('double tungid',),'double-tongued'), # Wycl Pro 8:13
    (('drynck offerynge','drinke offering','drink offering','drinke offring','drinke-offering','drynkofferinge','drinkofferinge','drynkofferynge','drynkoffrynge'),'drink-offering'),
    (('doung hill','dounghille','dounghill','dounghyll','dunghill','dunghil'),'dung-hill'), # Lam 4:5
    ((' eere ryngis ',' eareringes ',' earynges ',' earings '),' earrings '),((' eere ryng',' eare-ring'),' earring'), # Hos 2:13
    ((' eventide',' even tyde',' euentide',' euentid'),' eventide/evening'),
    (('euill doers','euil doers','evil doers','evildoers'),'evil-doers'),
    (('eye lids','eye liddes','eye lyddes'),'eyelids'),
    (('eye sight',),'eyesight'),
    (('fare wel ',),'farewell '),
    (('first borne','first-borne','firstborne','firstborn'),'first-born'), # 1Ki 16:34
    (('firste fruytis','first fruites','first fruits','first frutes','firstfruits'),'first-fruits'), # 2Ki 4:42, Neh 10:35
    (('fishe pooles','fish pooles','fishpools'),'fish-pools'), # Sng 7:4
    ((' go forth with ',),' go_forth_with '),
        ((' forthwith',' forth with',),' forthwith/immediately'), # KJB-1611 Mrk 1:29
        (('go_forth_with',),'go forth with'), # Got to be careful here -- this one overreaches: ((' forth with ',),' forthwith '),
    ((' fote me.',),' footmen.'), # 2Sam 15:1
    ((' fote stole',' footestoole',' footstoole',' footestole',' fotestole'),' footstool'), # Psa 99:5
    ((' for ever and ever',' for euer and euer',),' **FEandE**'), # Psa 145:1
    ((' for evermore',' for euermore',),' forever'), # Psa 86:12, 89:37
    (('Foreuer',),'Forever'),((' for ever ',' for euer ',' foreuer '),' forever '), # Might be 'for ever and ever' but caught above, e.g., Psa 10:16
    (('For ever,',),'Forever,'),((' for ever,',' for euer,',' foreuer,'),' forever,'),((' for ever.',' for euer.',' foreuer.'),' forever.'),((' for ever?',' for euer?',' foreuer?'),' forever?'),((' for ever;',' for euer;'),' forever;'),((' for ever:',' for euer:'),' forever:'),
    (('**FEandE**',),'for ever and ever'), # Psa 145:1
    (('fishe hookes','fish hookes','fish-hookes','fishhooks'),'fish-hooks'),
    ((' four folde',),' fourfold'),
    (('fourscore','foure score','foure scoor','four score','fourescore','fourescoore','fourescoor'),'fourscore/eighty'),
    (('Foure square',),'Foursquare'),(('foure square',),'foursquare'),
    (('freewill offering','free will offering','freewil offring','free-will offering','frewil offeringe'),'freewill-offering'),
    (('gogil iyed',),'goggle-eyed'), # Wycl Mrk 9:46
    (('grape gatherers',),'grape-gatherers'), # KJB-1611 OBA 1:5
    (('grape gleanings','grapegleanings'),'grape-gleanings'), # KJB MIC 7:1
    (('gray headed','grayheaded'),'gray-headed'), # Psa 71:18
    (('guest-chamber','guest chamber','guestchamber'),'guest-chamber/room'), # Mrk 14:14
    ((' hale stone',' haylestone',' hailestone'),' hailstone'),
    (('hand maidis',),'handmaids'), # Wycl Deu 28:68
    (('handy worke','hondy worke','hadye worke','handywork'),'handiwork'),
    ((' head stone',),' headstone'),
    (('healthoffrynge','healthoffringe'),'health-offering'),
    (('heaue offerynge','heaueoffringe'),'heave-offering'),
    (('hence forth','hece forth','hencefoorth','hensforth'),'henceforth'),
    ((' her selfe',' her silfe',' her self',' hir silf',' hir selfe',' hir self',' hirselfe',' herselfe',' hirself'),' herself'),
    ((' hid things',),' hidden things'),
    ((' hill’s side',' hilles side',' hilles syde'),' hillside'),
    ((' hym silf',' hym selfe',' him selfe',' him sylfe',' him silf',' hem silf',' hym sylf',' himsilfe',' himselfe',' hymselfe',' hemsilf'),' himself'),
    ((' hither to',' hidur to'),' hitherto'),
    ((' honie combe',' hony coomb',' hony combe',' hony cobe',' honycoomb'),' honeycomb'), # Sng 4:11
    ((' horse men',),' horsemen'),
    (('Hos anna','Hosyanna','Osanna'),'Hosanna'), # TNT Mrk 11:9
    ((' housse toppe',' house toppe',' house top',' house-top'),' housetop'), # Mkr 13:15
    ((' houndred foolde',' hundred folde',' hundred fold',),' hundredfold'), # Mrk 10:30
    ((' in deede',' in deed',' in dede',' indeede'),' indeed'), # Eze 18:19
    ((' in somoche',' insomuche',),' insomuch'), # Mrk 3:10
    ((' in steade ',' in steede ',' in stead ',' in stede '),' instead '),(('In steade ','In stead '),'Instead '),
    ((' it selfe',' it self',' it silfe',' it silf',),' itself'),
    ((' kinsmen',' kynes men',' kynnysmen',' kynsmen'),' kinsmen/relatives'),
    (('lande marke','londemarcke'),'landmark'), # Hos 5:10
    (('Lawgiuer',),'Law-giver'),((' law geuer',' lawgiver',' lawgiuer'),' law-giver'), # Psa 60:7
    (('long-suffering','longesuffrynge','longsuffering','long suffering','longe sufferinge'),'long-suffering/patient'),
    ((' long wing’d',' longwinged'),' long-winged'),
    ((' lyfe time',' life time'),' lifetime'),
    ((' lyke wyse',),' likewise'),
    (('louinge kyndnesses','louynge kyndnesses','louing kindnesses','louyng kyndnesses','lovingkindnesses'),'loving-kindnesses'),
    (('louinge kyndnesse','louynge kyndnesse','louyng kindnesse','louinge kindnesse','louing kindenesse','louing kindnesse','loving kindness','louing kindnes','lovingkindness'),'loving-kindness'),
    (('maid seruants','mayd servants','maidservants'),'maid-servants'),
    (('man seruants','manservants'),'man-servants'),
    (('many foold','many fold'),'manyfold'), # Psa 62:2, Hos 8:12
    ((' market place',),' marketplace'), # Tob 2:3
    (('meate offeringe','meate offering','meate offeryng','meate offring','meat offering','meat offring','meate-offering','meatofferinge','meatofferynge','meatoffringe','meatoffrynge'),'meat/grain_or_gift-offering'),
    (('meate & drink-',),'meat/grain_or_gift-offering & drink-'),
    (('money chaungeris','money chaungers','money changers','moneychangers'),'money-changers'),
    (('meane tyme','meane time','mean time'),'meantime'),
    (('mylne stoon','mylstone','milstone'),'millstone'), # Wycl Mrk 9:41
    ((' my selfe',' my self',' my silf',' myselfe',' myselff'),' myself'),
    (('neck bande','neckband'),'neck-band'), # Sng 1:11
    (('needle worke','needlework'),'needle-work'), # Psa 45:14
    ((' no where ',),' nowhere '),
    (('oure selues','our selues','oureselues'),'ourselves'),
    (('ouerbody cote',),'overcoat'),
    ((' out stretched',),' outstretched'), # KJB-1611 Jer 21:5
    (('palmer worme','palmerworm'),'palmer-worm'),
    (('peace offering','peace offring'),'peace-offering'),
    (('plowe shares','ploweshares','plowshares'),'plough-shares'),
    (('salte pitte','salt pitte','salt pit','saltpit'),'salt-pit'),
    (('Sea side',),'Seaside'),(('sea syde','sea side','seesyde' ,'seeside'),'seaside'),
    (('seuen folde','seuen fold','sevenfolde','seuenfoold','seuefolde'),'sevenfold'), # Psa 79:12
    (('sheepe coate','sheepe-cote','sheepecote'),'sheepcote'),
    (('Shew-bread',),'Show-bread'),(('shew bread','shewbread','shewbred'),'show-bread'), # 1Chr 9:32
    (('shippe fulles',),'shipfuls'), # Cvdl Deu 28:68
    (('side-chamber','side chamber'),'side-chamber/room'), # Eze 41:5
    (('sin offering','sinne offering','sinne offring','sinne-offering','synofferynge','synoffrynge'),'sin-offering'),
    (('sixty folde','sixtie folde','sixti fold','sixty fold','sixtyfold'),'sixty-fold'), # Mrk 4:20
    (('some thing',),'something'), # KJB-1611 Tob 5:15
    (('south warde','southwarde'),'southward'), # Cvdl Eze 47:1
    (('sted fastly','stedfastlie','stidfastli'),'steadfastly'), # Psa 119:106
    (('stiffe necked',),'stiff-necked'),
    (('stout hearted','stouthearted'),'stout-hearted'), # Psa 76:5
    (('strayght waye','streight waye'),'straightway'),
    (('stronge holdi','stronge holde','strong holde','stroge holde','strong hold'),'stronghold'), # Hos 10:14
    (('table fulles',),'tablefuls'), # Mrk 6:39
    (('taske maisters',),'taskmasters'),
    (('thankes geuynge','thankes geuing','thankesgeuynge','thankesgeuyng','thankesgeuing','thakesgeuynge','thankesgiuing','thanksgiuing','thankes-giuing'),'thanksgiving'),
    (('thankofferynge',),'thank-offering'),
    (('them silf',),'themself'),
    (('them selues','them selves'),'themselves'),
    ((' there ynne',' ther ynne',' therynne',' therin'),' therein'),
    (('thritti fold','thirtie folde','thirty folde','thirty fold','thirtyfold'),'thirty-fold'), # Mrk 4:20
    (('thorow out','thoroughout'),'throughout'), # 2Chr 17:19
    ((' three folde',' thre folde',' threefolde',' threfolde',' threefold'),' three-fold'), # Ecc 4:12
    (('threshing floore','threshingfloor'),'threshing-floor'), # Dan 2:35
    ((' thunder bolte',' thoder bolte',' thunder-bolt',' thunderbolte'),' thunderbolt'), # Psa 78:48
    (('thyself','thy selfe','thy selff','thi silf','yi self'),'thyself/yourself'), # Hos 13:9
    (('To day ','Todaye '),'Today '),((' to day ',),' today '),((' to dai,',),' today,'),
    (('To morrowe','To morowe','To morrow','To morow','Tomorow'),'Tomorrow'),
    ((' to gedder',' to ggedre',' to geder',' to gidere',' to gidir'),' together'),
    (('turtle doue','turtledove'),'turtle-dove'), # Psa 74:19
    ((' twy light',),' twilight'), # Eze 12:7
    (('vouche saaf',),'vouchsafe'), # Wycl Tob 12:4
    (('wash-pot','wash potte','wash pot','washpotte','washpot'),'wash-pot/bowl'), # Psa 60:8, 108:9
    (('water flood','water fludde','waterflood'),'water-flood'),
    (('wellbeloved','welbeloued'),'well-beloved'), # Sng 1:13
    (('well fauoured','well fauored','wel-fauoured'),'well-favoured'), # Sng 1:16
    ((' wine fat',' winefat'),' wine-fat/vat'), # KJB-1769 Mrk 12:1
    (('wynepresses',),'wine-presses'),(('wine presse ','wyne presse ','winepresse ','wynepresse '),'wine-press '),((' winepresse,',' wynepresse,',),' wine-press,'), # Joel 3:13
    ((' with drawen',),' withdrawn'), # Psa 5:6
    (('with ynne',),'within'),
    (('with outen','with oute'),'without'), # Eph 2:12
    ((' whorle winde',' whirle winde'),' whirlwind'),
    (('Whoso ','Who so '),'Whoso/Whoever '),((' whoso ',' who so '),' whoso/whoever '), # Dan 3:6
    (('whom soeuer ',),'whomsoever '),
    (('wood offering',),'wood-offering'),
    ((' you silf',),' yourself'),
    (('yourselues','youre selues','your selues','yor selues'),'yourselves'),

    # Three words into one word
    (('an hundreth folde',),'a hundred-fold'), # Gnva Mrk 4:8
    (('bred to eat',),'bread to eat'),
    (('lengthe and breede',),'length and breadth'), # Wycl Rev 21:16
        (('as is the breede',),'as is the breadth'), # Wycl Rev 21:16
    (('the high waye','the high way'),'the highway'),
    (('whither so euer',),'whithersoever'),
    (('who so euer',),'whosoever'),

    # One word into two
    # (('almsdeeds',),'alms deeds'), # Tob 1:3
    (('almesdedis','almsdeeds'),'giving_alms/donations'), # Tob 14:11
    (('arme-holes',),'arm holes'), # Jer 38:12
    (('Aswell ',),'As well '),((' aswell ',),' as well '), # Psa 87:7
    (('Assoone','Assone'),'As soon'),((' assoone ',' assone '),' as soon '), # Mrk 5:36
    ((' asure ',),' a sure '), # Isa 22:23
    ((' awhyle',),' a while'), # Mrk 6:31
    (('brokenhearted','broken hearted','broken harted'),'broken-hearted'), # KJB-1611 Luk 4:18
    (('broughtforth',),'brought forth'), # KJB-1611 Psa 90:2
    (('charet-cities',),'chariot cities'), # KJB-1611 2Chr 1:14
    (('charetman',),'chariot man'), # KJB-1611 2Chr 18:33
    (('couchingplace','couching place'),'couching-place/pen'), # Eze 25:5
    (('dounggate','doung gate'),'dung gate'),(('Donggate',),'Dung Gate'), # KJB-1611 NEH 12:31
    (('dwellingplaces',),'dwelling places'),
    ((' eastdore',),' east door'), # Eze 43:4
    ((' eastsyde',),' east side'), # 1Chr 9:18
    (('Eastwinde',),'East wind'), # Psa 78:26
    ((' eated',),' were eating'), # Psa 53:4
    (('euery-day',),'every day'),
    (('ewe-lambe',),'ewe lamb'), # KJB-1611 Lev 14:10
    (('Figtree',),'Fig tree'),((' figgetree',' fygetree',' figtree'),' fig tree'), # Hos 2:12
    (('firstripe',),'first ripe'), # Hos 9:10
    (('fish-gate','fishgate','fishe gate'),'fish gate'),(('Fyshgate',),'Fish Gate'), # KJB-1611 NEH 12:39
    (('Forsomuch',),'For so much'), # Bshps Eze 34:21
    (('fountaine-gate',),'fountain gate'), # KJB-1611 NEH 12:37
    (('grapegatherers',),'grape-gatherers'), # KJB-1769 OBA 1:5
    (('Gopher-wood',),'Gopher wood'), # KJB-1611 Gen 6:14
    (('helfire',),'hell fire'), # KJB-1611 Mrk 9:47
    (('holyday',),'holy day'), # KJB-1611 NEH 10:31
    (('horsegate',),'horse gate'),(('Horsgate',),'Horse Gate'), # Neh 3:28
    (('lefthalf',),'left-hand'), # Wycl Mrk 10:40
    (('lionlike',),'lion-like'), # KJB 1Chr 11:22
    (('lytelons',),'little ones'), # TNT Mrk 9:42
    (('namessake',),'name’s sake'), # Cvdl Mrk 13:9
    (('Newmoone',),'New Moon'),((' newmoone',' neomenye',' newmone',' newe moone',' new moone'),' new moon'), # 2Chr 31:3, Hos 2:11
    ((' noman ',),' no man '),((' noman,',),' no man,'), # Deu 32:39, Lam 4:4
    ((' nomore',),' no more'), # Hos 9:15
    (('Northwinde',),'North wind'),(('northwynde',),'north wind'), # Sng 4:16
    (('ofttimes',),'often times'), # KJB-1769 Mark 9:22
    (('oketrees',),'oak trees'), # Isa 1:29
    ((' outwent ',),' arrived before '), # Mrk 6:33
    (('Palme-tree',),'Palm tree'), # Eze 41:19
    (('riythond','riythalf'),'right-hand'),
    (('selfsame','selfe same'),'self-same'), # Eze 40:1
    (('shalbe ',),'shall be '),(('shalbe,',),'shall be,'),(('shalbe.',),'shall be.'),(('shalbe:',),'shall be:'),#(('shalbe<',),'shall be<'),
    (('sheepegate','sheepe-gate'),'sheep gate'),(('Shepegate',),'Sheep Gate'), # Neh 3:32
    (('Southwinde',),'South wind'),(('southwynde',),'south wind'), # Psa 78:26, Sng 4:16
    (('spearestaffe',),'spear staff'),
    (('store-cities',),'store cities'), # 2Chr 8:4
    (('stumblingblock','stumblyng blocke','stumbling blocke','stumbling block'),'stumbling-block'), # Eze 7:19
    (('water-gate',),'water gate'),(('Watergate',),'Water Gate'), # KJB-1611 NEH 12:37
    ((' wilbe ',' wylbe '),' will be '), # Sng 1:4
    (('yongemen',),'young men'),

    # Americanisms
    (('baptiz',),'baptis'),

    # Punctuation
    (('womans',),'woman’s'),(('womens',),'women’s'),


    # Other single words
    # (('A ',),'A '), # Wycliffe PSA 99:1
    (('Aarons',),'Aaron’s'),
            ((' abatid',),' abated'),
            ((' abhorre ',),' abhor '),((' abhorre.',),' abhor.'),((' abhorre:',),' abhor:'),
            ((' abididen',),' abided'),((' abidest',' abydest'),' abidest/abide'),((' abideth',' abydeth'),' abideth/abides'),(('abydinge','abidynge','abidinge'),'abiding'),((' abiden',),' abiding'),
                    (('Abyde',),'Abide'),((' abyde ',),' abide '),((' abyde,',),' abide,'),
                ((' abilitie ',' abilyte '),' ability '),((' habilitie,',' abilitie,'),' ability,'),
            (('abhominably',),'abominably/revoltingly'),(('abominable','abhomynable','abhominable','abhomible'),'abominable/revolting'),
                (('abominations','abhomynaciouns','abhomynacouns','abhominacions','abhominations'),'abominations/disgusting_things'),(('abomination','abhomynacioun','abhomynacoun','abhominacion','abhomination','abominacion','abhominacio'),'abomination/disgusting_thing'),
                ((' aboute',),' about'), (('Aboue',),'Above'),((' aboue',),' above'), #((' aboue,',),' above,'),((' aboue.',),' above.'),
            ((' abroade',' abrode',' abrood'),' abroad'),
            ((' absteyner',' abstayner'),' abstainer'),((' abstayne ',' absteyne '),' abstain '),
            (('aboundaunce','aboundance','abundaunce','abundauce'),'abundance'), (('abundaunte','aboundaunt','abundaunt','aboundant'),'abundant'),
        ((' accepte ',),' accept '),
                ((' accomplishe ',),' accomplish '),
                    (('Acordinge','Accordyng'),'According'),(('accordinge','acordynge','acordinge','accordyng'),'according'), ((' accorde ',' acorde '),' accord '),((' acord',),' accord'),
                    ((' accomptes ',' accompts '),' accounts '),
            (('acknowledgeth','knoulechith'),'acknowledgeth/acknowledges'),(('knoulechide',),'acknowledged'),
            (('acquaintaunce','acquauntaunce','acquantaunce','acquataunce'),'acquaintance'),
            ((' acris',' akers',),' acres'),
            (('Actes,',),'Acts,'),(('Actes:',),'Acts:'),((' actes',),' acts'), #((' actes,',),' acts,'),((' actes.',),' acts.'),((' actes:',),' acts:'),
                ((' actiue',),' active'), ((' actiuitie ',),' activity '),((' actiuitie,',),' activity,'),
        (('Adde ',),'Add '),((' adde ',),' add '),((' adde,',),' add,'),((' adde)',),' add)'),
            ((' adiure',),' adjure'),
            ((' aduoutrers',),' adulterers'),(('auoutressis',),'adulteresses'),(('adulteresse)',),'adulteress)'),(('adultresse,','auoutresse,'),'adulteress,'), (('avowtresse','aduouterous','advoutrous'),'adulterous'),
                ((' auowtries',' auoutries'),' adulteries'),((' adulterie ',' aduoutry ',' advantry ',' auowtri '),' adultery '),((' adulterie,',' aduoutrye,',' aduoutry,',' auoutrie,',' auowtrie,'),' adultery,'),((' adulterie.',' aduoutrie.',' advoutrie.'),' adultery.'),((' adulterie:',),' adultery:'),((' auowtrie;',),' adultery;'),
            (('advantageth','auauntageth','a vauntageth'),'advantageth/advantages'), (('aduantage','auauntage'),'advantage'),
                ((' aduersaries',' aduersaryes'),' adversaries'),((' aduersarie',' aduersary',),' adversary'), ((' aduersities',),' adversities'),((' aduersitie ',' aduersite '),' adversity '),((' aduersite,',),' adversity,'),((' aduersitie.',' aduersite.'),' adversity.'),((' aduersitie:',' aduersite:'),' adversity:'), ((' aduice ',),' advice '), ((' aduise',),' advise'),
        ((' afer,',),' afar,'),((' afer.',),' afar.'),((' afer;',),' afar;'),
            ((' affaires',),' affairs'), ((' affinitie ',),' affinity '), ((' affliccioun',' affliccion',' afflictiō'),' affliction'),
            ((' affrayde',' afrayed',' afrayde',' afrayd',' afraide',' afraied',' afeerd',' aferd'),' afraid'),
                ((' afresshe',),' afresh'),
            (('Afterwarde',),'Afterward'),((' afterwarde',' aftirward'),' afterward'), (('Aftir',),'After'),((' aftir ',' afer ',' eft '),' after '),((' aftir;',),' after;'),
        (('ayenstonde',),'stand_against'), (('Agaynst',),'Against'),((' agaynste',' ageynste',' ageynst',' agaist',' ayenus',' ayenst',' ayens'),' against'),(('agaynst',),'against'), (('Agayne','Againe'),'Again'),((' ayen ',),' again '),((' ageyne,',' ayen,'),' again,'),((' ayen.',),' again.'),((' ayen?',),' again?'),((' ayen;',),' again;'),((' agayne',' ageyne',' againe'),' again'),
                ((' agaste',),' aghast'),
            ((' agonye',' agonie'),' agony'),
            ((' aggreed',),' agreed'),((' agrement',),' agreement'),
        (('Ahaua',),'Ahava'),
        ((' ayde ',' aide '),' aid '),((' ayde,',),' aid,'),((' ayde.',),' aid.'),((' ayde:',),' aid:'),
            ((' ayled',),' ailed'),((' aileth',' ayleth'),' aileth/ails'),
            ((' aire ',' ayre ',' eyr '),' air '),((' aire,',' ayre,',' eir,'),' air,'),((' ayer.',' eir.'),' air.'),((' ayre:',' aire:'),' air:'),((' eir;',),' air;'),
        ((' alablaster',),' alabaster'),
            ((' alarme ',' alarum '),' alarm '),((' alarme,',),' alarm,'),((' alarme.',),' alarm.'),
            ((' aliens',' aliauntes',' aleauntes',' aliantes',' alients'),' aliens/foreigners'),((' alien ',' aliaunt ',' aliant '),' alien/foreign(er) '),
                ((' aliue',' alyue',' alyve'),' alive'),
            (('Alle ','Al '),'All '),((' alle ',' al '),' all '),((' alle,',' al,'),' all,'),((' alle.',),' all.'),((' alle:',),' all:'),((' alle;',),' all;'),
                # For allow, see below after ALOUD ((' alow',),' allow'),
            (('Allmightie','Almightie'),'Almighty'),((' almightie',' almyyti'),' almighty'),#((' almightie:',),' almighty:'),
                ((' allmost',' almest'),' almost'),
                (('Alms','Almes'),'Alms/Donations'),((' alms',' almes'),' alms/donations'),
            ((' aloone',),' alone'), ((' aloude',' alowde',' alowd'),' aloud'), ((' alow',),' allow'),
            ((' alreadie',' allready',' allredy',' alredy'),' already'),
            ((' altare',' aulter',' auteri',' auter'),' altar'), ((' alltogether',),' altogether'),
        (('amased',),'amazed'),
            (('Embassitour',),'Ambassador'),(('ambassadour','embassadour'),'ambassador'),
            ((' amendement',' amendemet'),' amendment'), ((' amendid',),' amended'),((' amendyng',),' amending'),((' amendes',),' amends'),((' amende ',' amede ',),' amend '),
            ((' amisse',' amysse'),' amiss'),
            (('Amonge ',),'Among '),((' amongest ',' amongst ',' amonge ',' amoge ',' amog '),' among '),(('(amonge ',),'(among '),
        ((' auncient',),' ancient'),
            (('Aud ',),'And '),((' ad ',),' and '), (('Andrewe',),'Andrew'),
            (('Angell',),'Angel'),((' aungeli',' aungel',' angell'),' angel'),
                ((' angred',),' angered'), ((' angrie ',),' angry '),((' angrie,',' angrye,'),' angry,'),((' angrie?',),' angry?'),((' angrie!',),' angry!'),((' angrie:',),' angry:'),
                ((' angwischid',' angwisched'),' anguished'),((' anguishe ',),' anguish '),((' angwische',' angwisch'),' anguish'),
            ((' anoiede',' anoyed'),' annoyed'),((' anoye ',),' annoy '),
            (('Annoynted','Annointed','Anoynted'),'Anointed'),(('anoyntiden','anoyntide','anoyntid','anointide','annoynted','anoynted','annointed'),'anointed'),((' annoynt',' annoint',' anoynte',' anoynt'),' anoint'),
                ((' anoon ',' anone ',' anon '),' anon/immediately '), (('Anothir',),'Another'),
            (('Answerest','Answerist'),'Answerest/Answer'), (('Aunswer',),'Answer'),((' aunswer',),' answer'), (('answeryden','answerden','answerede','answerde','answeriden','answeride','answerid','answeren'),'answered'),((' answeryng',),' answering'), (('Answere ',),'Answer '),((' answere ',),' answer '),((' answere,',),' answer,'),((' answere.',),' answer.'),((' answere?',),' answer?'),((' answere:',),' answer:'),
                # (('answerden','answerede','answerde','answeriden','answeride','aunswered'),'answered'),((' answeryng',),' answering'), (('Aunswere ','Answere '),'Answer '),((' aunswere ',' answere '),' answer '),((' aunswere,',' answere,'),' answer,'),((' aunswere.',' answere.'),' answer.'),((' aunswere:',' answere:'),' answer:'),
            ((' ony ',' eny '),' any '),((' eny,',),' any,'), (('enythinge',),'anything'),
        ((' aparte',),' apart'),
            (('apostlis','apostels'),'apostles'),
            ((' apparell',),' apparel'), ((' apparaunt',),' apparent'),
                (('appearaunce',),'appearance'),(('appearynge','apperynge','apperinge','apperenge','appearyng'),'appearing'),((' apperiden',' appered',' apperide',' apeared',' apperid',' apered'),' appeared'),((' appeareth',' apeareth'),' appeareth/appears'), ((' appeare ',' appere '),' appear '),((' appeare,',' apeare,'),' appear,'),((' appeare:',),' appear:'),
                    ((' appertaineth',),' appertaineth/appertains/relates_to'), ((' appertain ',' appertaine '),' appertain/relate_to '),((' appertain,',' appertaine,'),' appertain/relate_to,'),
                ((' applis',),' apples'),((' appil ',' aple '),' apple '),
                    (('applyed',),'applied'),((' applye ',' applie '),' apply '),
                ((' appoyntmet',),' appointment'), (('appoynted','apoynted'),'appointed'),(('appoynte','apoynte','appoynt'),'appoint'),
                ((' approche ',' approch '),' approach '),((' approche,',),' approach,'),
                    ((' approue',),' approve'),
                ((' apte ',),' apt '),
        (('archaungel',),'archangel'), ((' archeris',),' archers'),
            (('Aryse',),'Arise'),((' aryse',),' arise'),
            (('Ark ','Arcke ','Arke ',),'Ark/Box '),(('Ark,','Arke,'),'Ark/Box,'),(('Ark.','Arke.'),'Ark/Box.'),((' arcke',' arke'),' ark/box'),((' ark ',),' ark/box '),((' ark,',),' ark/box,'),#((' arke,',),' ark/box,'),((' arke:',),' ark/box:'),
            ((' arme ',),' arm '),((' arme,',),' arm,'),((' arme.',),' arm.'),((' arme?',),' arm?'),((' arme:',),' arm:'),((' arme;',),' arm;'),((' arme)',),' arm)'),
                ((' armorie,',),' armoury,'), ((' armuris',),' armours'),
                ((' armes',),' arms'), ((' armie ',' armye '),' army '),((' armie,',),' army,'),((' armie.',),' army.'),((' armie?',),' army?'),((' armie:',),' army:'),
            ((' aroose',),' arose'),
            ((' arayed',),' arrayed'), ((' arraye ',' araye ',' araie ',' aray '),' array '),((' araye,',),' array,'),((' araye.',' aray.'),' array.'),
                ((' arriue',),' arrive'),
                ((' arrogancie,',),' arrogancy,'), ((' arewis',' arowis'),' arrows'),((' arrowe',' arowe',' arewe'),' arrow'),
            (('Art ','Arte '),'Art/Are '),((' arte ',),' art '),
        (('ascencioun',),'ascension'), ((' ascende ',),' ascend '),((' ascende,',),' ascend,'),
                (('Asscribe','Ascrybe'),'Ascribe'),((' ascrybe',),' ascribe'),
            (('asshamed','aschamed','aschamid'),'ashamed'), ((' asshes',' aischis'),' ashes'),((' aische,',),' ash,'),((' aische.',),' ash.'),
            ((' asidis',' asyde'),' aside'),
            ((' asleepe',' aslepe'),' asleep'),
             ((' askeden',' axeden',' axiden',' axide',' axed'),' asked'), (('Askest','Axist'),'Askest/Ask'),((' askest',' axist'),' askest/ask'), (('Aske ',),'Ask '),((' aske ',),' ask '),((' aske.',' axen.',' axe.'),' ask.'),((' aske?',),' ask?'),((' aske:',),' ask:'), ((' to axe ',),' to ask '),
            ((' assis ',),' asses '), (('Asse ',),'Ass '),((' asse ',),' ass '),((' asse,',),' ass,'),((' asse.',),' ass.'),
                ((' assailide',' assayled'),' assailed'), ((' assaileth',' assailith'),' assaileth/assails'), ((' assaile ',),' assail '),
                ((' assemblie ',),' assembly '),((' assemblie,',' assemblye,'),' assembly,'),((' assemblie:',),' assembly:'),((' assemblie)',),' assembly)'), ((' assente ',),' assent '),
                ((' aswagid',),' assuaged/lessened'), ((' aswagist',),' assuagest/lessen'),
            (('astonnied','astonied','astonneyd','astonnyed','astonyed'),'astonished'),
                ((' astraye',' astraie'),' astray'), (('astromyenes',),'astronomers'),
        ((' eet;',),' ate;'),
            ((' athyrst',),' athirst'),
            ((' attonement',),' atonement'),
            ((' attayned',' atteined'),' attained'),((' attayne ',' attaine '),' attain '),
                ((' attendaunce',' attedaunce'),' attendance'), (('Attende ',),'Attend '),((' attende ',),' attend '), (('attentiue',),'attentive'),
                ((' atier',),' attire'),
        (('aucthoritie','auctoritie','authoritie','auctorite'),'authority'),
        ((' auailed',),' availed'),((' availeth',' auaileth'),' availeth/avails'),((' auaile ',),' avail '),
                ((' avaricious',' auaricis'),' avaricious/greedy'),
            (('Auen',),'Aven'),((' avengeth',' auengeth'),' avengeth/avenges'),((' aueng',' aueg'),' aveng'),
                ((' auerse',),' averse'),
            (('Auoyde','Avoyde'),'Avoid'),((' auoyd',' auoid'),' avoid'),
        (('Awaye ',),'Away '),((' awaye',' awaie',' awei',' awey',),' away'),((' awai.',),' away.'),
    ((' backes',' backis'),' backs'),((' backe ',' bak '),' back '),((' backe,',' bak,'),' back,'),((' backe.',),' back.'),((' backe?',),' back?'),((' backe:',),' back:'),((' bak;',),' back;'),
                (('bacbitiden',),'backbiting'), (('backewarde','backeward','backwarde','bacward'),'backward'),
            ((' bagge ',),' bag '),
            ((' bakere',),' baker'), ((' baken',),' baked'),((' bakynge',' bakun'),' baking'),
            (('ballaunce','ballance','balaunce'),'balance'),
                (('baldnesse','ballidnesse'),'baldness'),((' baldnes ',),' baldness '),((' baulde ',' balde ',' ballid '),' bald '),((' balde:',),' bald:'),
                ((' baulmes',),' balms/ointments'),((' balme',),' balm/ointment'),
            (('Bandes',),'Bands'),((' bandes',),' bands'),
                ((' banishmet',),' banishment'), ((' banyshed',),' banished'),
                ((' banckes',' bankes'),' banks'),((' banck ',' banke '),' bank '),
                ((' banketting',),' banqueting'),((' banket',),' banquet'),
            (('baptysed','baptisid'),'baptised'), (('baptisynge','baptisyng'),'baptising'), (('baptisme','baptyme','baptym'),'baptism'), ((' baptyse',),' baptise'),
            ((' barres',' barris'),' bars'),((' barre ',),' bar '),((' barre.',),' bar.'),
                ((' barbour',),' barber'),
                ((' barefoote',),' barefoot'),
                ((' barke ',),' bark '),
                ((' barlye',' barlie',' barli',' barly'),' barley'),
                ((' barne',),' barn'), #((' barne?',),' barn?'),
                ((' barrell',),' barrel'),
                ((' bareynesse',),' barrenness'), ((' bareyn ',' baren '),' barren '),
            ((' basons',' basens'),' basins'),
                (('basskettes','baskettes','basketes'),'baskets'),
                (('bastards','bastardes'),'bastards/out_of_wedlock'),(('bastard ','bastarde '),'bastard/out_of_wedlock '),
            ((' battayls',' batels'),' battles'), ((' battaile',' battayll',' battayle',' battell',' battel',' batayll',' batell',' batel'),' battle'),
            (('Bauai',),'Bavai'),
            ((' baye ',),' bay '), # PSA 37:36 Bay tree
        (('Bee ',),'Be '),((' bee ',),' be '),((' bee,',),' be,'),((' bee?',),' be?'), #(('>bee<',),'>be<'),((' bee<',),' be<'),
            ((' beames',),' beams'),((' beame ',' beem '),' beam '),((' beame,',),' beam,'),((' beame.',),' beam.'),
            ((' beanes',),' beans'),
                ((' bearest',' berist'),' bearest/bear'),
                    (('Beares','Beeres'),'Bears'),((' beares ',' beeris '),' bears '), # Protect 'bearest'
                        (('Beare ',),'Bear '),(('Beare,','Bere,'),'Bear,'),((' beare ',' beere ',' bere '),' bear '),((' beare,',' bere,',),' bear,'),((' beare.',),' bear.'),((' beare:',),' bear:'),
                    ((' beerdes',' beerdis',' beardes'),' beards'),((' beerd',' berd'),' beard'),((' bearde,',' beerde,'),' beard,'), ((' beareth',' berith',' bereth'),' beareth/bears'), ((' bearinge',' bearynge',' beringe',' berynge',' beryng',' beren'),' bearing'),
                (('Beasts ','Beastes ','Beestis '),'Beasts/Animals '),(('beasts','beastes','beestes','beestis'),'beasts/animals'),((' beesti',' beeste',' beest'),' beast/animal'),
                ((' betun',),' beaten'),((' beatinge',' beetynge',' betynge',' beeten'),' beating'), (('Beate ','Beete '),'Beat '),((' beate ',' beete ',' bete '),' beat '),((' bett,',),' beat,'),
                (('Beautifull ',),'Beautiful '),((' beautifull ',' beutifull ',),' beautiful '),((' beautifull,',' beutyfull,'),' beautiful,'), ((' beautifie ',),' beautify '), (('Beautie,',),'Beauty,'),((' beautie ',' beutie ',' bewtie ',' bewtye ',' bewty '),' beauty '),((' beautie,',' beutie,'),' beauty,'),((' beautie.',),' beauty.'),((' beautie?',),' beauty?'),((' beautie!',),' beauty!'),((' beautie:',' beuty:'),' beauty:'),
            ((' becometh',' becommeth',' bicometh'),' becometh/becomes'), ((' becomme',),' become'),
            ((' beeddes',' beddes',' beddis'),' beds'),((' beed ',' bedde '),' bed '),((' bedde,',' bedd,'),' bed,'),((' bedde.',' beed.'),' bed.'),
            (('Beerseba','Bersaba'),'Beer-sheba'), ((' beene ',' bene ',' ben ',' bin '),' been '),((' beene,',' bene,',' ben,'),' been,'),((' bene.',),' been.'),
            (('Bifore ',),'Before '),((' bifore ',' byfore ',' bifor '),' before '),((' bifore,',' bifor,',),' before,'),((' bifore.',),' before.'),((' bifore;',),' before;'),
            ((' beganne',' begane',' bigunnen',' bigan'),' began'), ((' bigat ',' begate '),' begat '),
                ((' beggere',' begger'),' beggar'), ((' beggide',),' begged'),((' begginge',' begyng'),' begging'), ((' begge ',' begg '),' beg '),((' begge:',),' beg:'),((' begge;',),' beg;'),
                (('Begynne ',),'Begin '),((' bigynne',' begyn',),' begin'), (('bigynnyngi','beginnynge','beginninge','bigynnyng','beginnyng','biginnyng'),'beginning'), ((' beginne ',),' begin '),
                (('bigetun ','begotte '),'begotten '),
                ((' beguiled',' begyled'),' beguiled/deceived'),((' beguile ',' begyle '),' beguile/deceive '), ((' bigunne',' begonne'),' begun'),
            ((' behalfe',),' behalf'), ((' behaue',),' behave'), ((' behauoure',' behauiour'),' behaviour'),
                ((' biheedide',' bihedide',' beheeded',' beheded'),' beheaded'), (('bihelden','biheelde','behelde','biheeld','bihelde'),'beheld'),
                ((' behinde',' bihynde',' behynde'),' behind'),
                ((' biholden',),' beholden'),((' biholdere',),' beholder'), ((' beholdeth',' biholdith'),' beholdeth/beholds'),((' biholdinge',' biholdynge',' biholdyng'),' beholding'),(('Biholde','Beholde'),'Behold'),((' biholdist ',' biholde ', ' beholde '),' behold '),((' beholde,',' biholde,',' byholde,'),' behold,'),((' beholde.',),' behold.'),((' beholde:',),' behold:'),
                    ((' bihoueth',),' behoves'),
            ((' beinge',' beynge',' beyng',' beeing'),' being'),
            ((' beliefe',),' belief'),
                    (('bileueden','bileuede','beleeued','beleued','beleved'),'believed'), ((' believest',),' believest/believe'),(('believeth','bileueth','beleueth','beleeueth','belevith'),'believeth/believes'),((' bileuynge',' bileuen'),' believing'), (('Bileue ','Beleeue ','Beleue ','Beleve '),'Believe '),((' beleue',' beleeue',' beleve',' bileue'),' believe'),
                ((' bels ',),' bells '),
                    ((' bellyes',),' bellies'),((' bellie ',' bely '),' belly '),((' bely,',),' belly,'),
                ((' belongeth',' belogeth'),' belongeth/belongs'),((' belonge ',),' belong '), (('beloued','beloven'),'beloved'),
            ((' bemoane ',),' bemoan '),
            ((' beendynge',' bendinge'),' bending'),((' bende ',),' bend '),
                ((' bynethe',' beneeth',' beneth'),' beneath'),
                    (('beneficiall ',),'beneficial '),(('beneficiall:',),'beneficial:'), (('benefites',),'benefits'),((' benefite:',),' benefit:'),
                (('Benhadad',),'Ben-hadad'),
                ((' benygneli',),' benignly'),((' benygne',),' benign'),
                ((' bente ',),' bent '),
                (('Beniamite',),'Benyamite'),(('BenIamin',),'BenYamin'),(('Beniamin','Beniamyn'),'Benyamin'),
            ((' biquest',),' bequest'),
            ((' bereaue',),' bereave'), (('Berill',),'Beryl'),
            (('beseeching','besechyng','bisechyng','biseching'),'beseeching/imploring'),((' bisechide',),' beseeched/implored'),(('beseeche ','beseech ','biseche ','beseche '),'beseech/implore '),(('biseche,','beseech,'),'beseech/implore,'),
                ((' besydes',' besidis',' bisidis'),' besides'), (('Besyde',),'Beside'),((' besyde',' biside'),' beside'), ((' bisegide',' bisegid',' beseged'),' besieged'),((' bisege ',' besege '),' besiege '),
                ((' beste ',),' best '), ((' bestowe ',),' bestow '),((' bestowe;',),' bestow;'),
            (('Bethanie ','Bethania ','Bethanye ','Betanye '),'Bethany '), (('Beth-auen','Bethauen'),'Beth-aven'), (('Bethlehe ','Bethlee '),'Beth-lehem '),(('Beth-leem','Bethleem'),'Beth-lehem'), #(('Bethleem,',),'Bethlehem,'),
                ((' betrayeth',' betraieth'),' betrayeth/betrays'),(('bitraiede','betraied','bitrayed','bitraied'),'betrayed'),(('bitraye ','betraye ','betraie ','bitray '),'betray '),
                (('Betere',),'Better'),((' bettere ',' betere ',' beter '),' better '), # Protect 'bettered'
                ((' bytwene',' betweene',' betwene'),' between'),
            (('Bewarre',),'Beware'),((' bewarre',),' beware'),
            ((' beyonde',' biyende',' biyondis',' beionde'),' beyond'),
        ((' byd ',),' bid '), ((' byde ',),' bide/stay '),
            ((' bygg ',),' big '), (('Biguai',),'Bigvai'),
            ((' billowes',),' billows'),
            ((' bindeth',' byndeth',' byndith'),' bindeth/binds'),(('Bynde ','Binde '),'Bind '),((' bynde ',' binde '),' bind '),
            ((' briddis',' byrdes',' birdes'),' birds'),((' byrde ',' birde ',' brid '),' bird '),((' byrde,',' brid,'),' bird,'),((' brid.',),' bird.'),((' birde:',),' bird:'),
                ((' birthe',' byrth'),' birth'),
            ((' biteth',' byteth',' betith'),' biteth/bites'),((' bytinge',),' biting'),((' byte ',),' bite '), ((' bytten',),' bitten'),
                (('Bitterne',),'Bittern/Heron'),((' bittern ',),' bittern/heron '),
                ((' bitternessis',),' bitternesses'),((' bitternesse ',' bytternesse ',' bytternes ',' bitternes '),' bitterness '),((' bitternes,',),' bitterness,'), ((' bittere',' bytter',' bittir'),' bitter'),
        ((' blackenesse',' blacknesse'),' blackness'), ((' blackere',),' blacker'), ((' blacke ',' blake '),' black '),((' blacke,',' blake,',' blak,'),' black,'),((' blacke:',),' black:'),
                ((' blamelesse',),' blameless'), ((' blameden',' blamyde'),' blamed'),((' blamyngi',' blamyng',),' blaming'),
                 ((' blasfemyes',),' blasphemies'),((' blasphemie ',' blasfemye '),' blasphemy '),((' blasphemie,',' blasfemye,'),' blasphemy,'),((' blasphemie:',),' blasphemy:'),((' blasfemye;',),' blasphemy;'),
                        ((' blasfemed',),' blasphemed'),(('blasphemeth ','blasfemeth '),'blasphemeth/blasphemes '),(('blasphemethe,',),'blasphemeth/blasphemes,'),((' blasfemen',),' blaspheme'),
                    ((' blastinge',),' blasting'),
            ((' blemishe',' blemysh'),' blemish'),
                (('Blessid ','Blissid '),'Blessed '),(('blessiden','blesside','blisside','blessid','blissid','blissed'),'blessed'),((' blessist',),' blessest/bless'), (('blessinge','blessynge','blessyngi','blessyng'),'blessing'), (('Blesse ',),'Bless '),((' blessen ',' blesse '),' bless '),((' blesse,',),' bless,'),((' blesse:',),' bless:'),
                ((' blewe ',),' blew '),
            (('blindnesse','blyndnesse','blyndnes'),'blindness'), ((' blynded',' blyndid'),' blinded'),
                (('Blynde ',),'Blind '),(('blynde ','blinde '),'blind '),(('blinde,','blynde,'),'blind,'),(('blinde.','blynde.'),'blind.'),(('blinde?','blynde?'),'blind?'),(('blynde:','blinde:',),'blind:'),(('blynd',),'blind'),
            (('blood-guiltinesse','bloudegyltynesse','bloodguiltiness'),'blood-guiltiness'), (('bloudthurstie','bloodthirstie'),'bloodthirsty'), ((' bloodie ',' blodi '),' bloody '),((' bloudie,',),' bloody,'), (('bloodis',),'bloods'),(('bloude','bloud'),'blood'),
                ((' blossomes',),' blossoms'),((' blossome ',),' blossom '),((' blossome,',),' blossom,'),((' blossome:',),' blossom:'),
                ((' blowinge',),' blowing'),((' blowen',),' blown'), (('Blowe ',),'Blow '),((' blowe ',),' blow '),((' blowe,',),' blow,'),((' blowe:',),' blow:'),
            ((' blont',),' blunt'),
        ((' bordes',' bords'),' boards'),
                ((' boostinge',' boastyng'),' boasting'), ((' boastes',),' boasts'),
                 ((' bootys',' boates'),' boats'),
            ((' bodili ',' bodely '),' bodily '), ((' bodyes',),' bodies'), ((' boddy ',' bodi '),' body '),((' bodie,',' bodi,'),' body,'),((' bodie.',' bodi.'),' body.'),((' bodi;',),' body;'),
            ((' boyled',),' boiled'), ((' boyle ',),' boil '),((' boile,',' boyle,'),' boil,'),
            ((' boldely',' booldly',' booldli'),' boldly'),((' boldnes ',),' boldness '), ((' bolde ',),' bold '),
            ((' bookis',' bokis',' bookes',' bokes'),' books'), (('BOOKE ',),'BOOK '),(('Booke ',),'Book '),((' booke ',' boke '),' book '),((' booke,',' boke,'),' book,'),((' booke.',' boke.'),' book.'),((' booke?',),' book?'),((' booke:',),' book:'),
                ((' boothes',' bothes'),' booths'), ((' bootes',' bootis'),' boots'),
            ((' boondis',' bondes',' bondys'),' bonds'),((' boond ',' bonde '),' bond '),(('bond-seruice','bondservice'),'bond-service'), ((' boonus',' boonys',' boones',' bonys'),' bones'),
            ((' borderyng',' borderinge'),' bordering'),((' boordes',),' borders'),
                ((' borow',),' borrow'),
                ((' borun ',' borne '),' born '),((' borun,',' borne,'),' born,'),((' borne.',' borun.'),' born.'),((' borne:',),' born:'),
            ((' bosome',' bosum'),' bosom'),
            ((' bothe ',),' both '),
                ((' bottell',' bottel',' botell',' botle'),' bottle'), ((' bottome',' botome'),' bottom'), (('bottomlesse',),'bottomless'),
            ((' bowis',),' boughs'),((' boughe',' boowi'),' bough'), ((' bouyt',),' bought'), ((' boundes',),' bounds'),((' boundun ',' bounde ',' boud '),' bound '),((' bounde,',),' bound,'),((' bounde:',),' bound:'), ((' bountie:',),' bounty:'),
            ((' bowiden',' bowide',' bowede',' bowid',' bowen'),' bowed'),((' bowynge',' bowyng'),' bowing'),((' bowes',),' bows'),((' boweth',' bowith'),' boweth/bows'),(('Bouwe ','Bowe '),'Bow '),((' bouwe ',' bowe '),' bow '),((' bouwe,',' bowe,'),' bow,'),((' bowe.',),' bow.'),((' bowe:',),' bow:'),
                ((' bowle',' boule',' boll'),' bowl'),#((' bowles',' boules'),' bowls'),((' bowle,',' boule,',' boll,'),' bowl,'),
            ((' boxe ',),' box '),((' boxe,',),' box,'),
            ((' boyes',),' boys'),
        ((' bracelette',),' bracelet'),
            ((' braynes',),' brains'),
                (('braunches','braunchis','brauches'),'branches'),((' braunche',' braunch'),' branch'), ((' brande ',),' brand '),
                ((' brasse ',' bras '),' brass '),((' brasse,',' bras,'),' brass,'),((' brasse.',),' brass.'),((' brasse:',),' brass:'),((' brasse;',' bras;'),' brass;'),
                ((' brawne',),' brawn'),
            (('breed ',),'bread '), ((' bredth',),' breadth'),
                    ((' breaketh',' brekith'),' breaketh/breaks'),((' breakynge',' breakinge',' brekynge',' brekyng'),' breaking'),(('Breake ',),'Break '),((' breake ',' breke ',),' break '),((' breake,',' breke,'),' break,'),((' breake:',),' break:'),
                    (('breastes','brestis','brestes','brests'),'breasts'),((' breast',' brest'),' breast/chest'),#((' breast,',),' breast/chest,'),((' breast.',' brest.'),' breast/chest.'),
                    ((' brething',),' breathing'), ((' breth ',),' breath '),((' breth,',),' breath,'),
                (('brethren','britheren',),'brethren/brothers'),(('brethre ',),'brethren/brothers '),(('brethre,',),'brethren/brothers,'),(('brithre.',),'brethren/brothers.'),(('brethre:',),'brethren/brothers:'),
            (('brickkiln','bricke-kill','brickyll'),'brick-kiln'), (('brycke','bricke','bryck'),'brick'),
                ((' bryde',),' bride'), ((' bridil',' brydle'),' bridle'),
                ((' bryer',),' brier'),
                (('briytnessis',),'brightnesses'),(('brightnesse ','brightnes ','briytness '),'brightness '),(('brightnes,',),'brightness,'),(('briyt ',),'bright '),
                ((' brimme ',),' brim '),
                (('bringest','bryngest'),'bringest/bring'),(('bringeth','bryngeth','bringith','bryngith'),'bringeth/brings'),(('brynginge','bryngynge','bringinge','bringige','bryngyng','bringyng','bryngen'),'bringing'), (('Brynge ','Bringe ','Bryng '),'Bring '),((' brynge ',' bryng ',' bringe '),' bring '),
                ((' brinke ',),' brink '),
            (('broddere',),'broader'),(('broddeste',),'broadest'), ((' broade ',' brode '),' broad '),((' brode.',),' broad.'),((' broade:',),' broad:'),
                ((' brokun',' breken'),' broken'), ((' braken ',' brak '),' broke '),((' brak,',),' broke,'),
                ((' brookes',' brokes'),' brooks'),((' brooke ',),' brook '),((' brooke,',),' brook,'),((' brooke.',),' brook.'),
                ((' brodel ',' bordel '),' brothel ' ), ((' brothir',),' brother' ),
                ((' broughtest',),' broughtest/brought'), (('broughte ','brouyte ','broughe '),'brought '),(('brouyten','brouyt'),'brought'),
                ((' browne',),' brown'),
            ((' brussed',' brused'),' bruised'),
                ((' bruite',),' brute'),
        ((' boket',' bokat'),' bucket'), ((' buckis',),' bucks'),((' bucke ',' buc ',' buk '),' buck '),
                (('buriownynge',),'budding'), ((' buddis',),' buds'),((' budde ',),' bud '),((' budde:',),' bud:'),
                ((' buylders',' bilderis',' bylders'),' builders'), ((' builded',' buylded',' bildiden',' bildide',' bildid',' builte',' buylt',' bylt'),' built'),
                    ((' buildest',' buyldest',' byldest',' bildist'),' buildest/build'),((' buildeth',' buyldeth',' bildith'),' buildeth/builds'),(('buyldynges','buildynges','byldynges','bildyngis','bildingis','byldinges'),'buildings'), (('Buylding',),'Building'),(('buildinge','buyldinge','buylding','bildyng','bilden'),'building'),
                    ((' buylde ',' buyld ',' builde ',' bylde ',' bilde '),' build '),((' buylde,',),' build,'),((' buylde.',' buyld.',' builde.',' bilde.'),' build.'),
            ((' boffeted',),' buffetted'),((' buffeti',),' buffet'),
            ((' bullocke',),' bullock'), ((' boolis',' bulles',),' bulls'), ((' bullworkes',' bulwarkes',' bulworkes'),' bulwarks'),
            ((' bundell ',' bundel '),' bundle '),
            ((' burthen',' birthun',' burthe'),' burden'),
                ((' burgler',),' burglar'),
                ((' buriest',' biriest'),' buriest/bury'),((' birieli',' buriall',' biriel'),' burial'),((' birieden',' biriede',' biried',' buryed',' biryed'),' buried'),((' buryinge',' biriyng'),' burying'),((' burie ',' byrie ',' burye ',' birie '),' bury '),
                ((' burnynge',' burnyng',' brennynge',' brennyng',' burnige'),' burning'),((' burned',' brenten',' brente',' brent',' bnrnt'),' burnt'),((' bret ',),' burnt '),((' burne ',' brenne '),' burn '),((' burne,',),' burn,'),((' burne.',),' burn.'),((' burne:',),' burn:'),
            ((' busshell',' busshel',' bushell',' buschel'),' bushel'), ((' busshe ',),' bush '),((' buysch,',' bushe,'),' bush,'),
                ((' bisili',),' busily'), ((' bysy ',' busie '),' busy '),((' bisi;',),' busy;'),
                ((' bisinessis',),' businesses'),((' businesse ',' busynesse ',' bisynesse ',' busynes ',' busines '),' business '),((' busynesse,',' businesse,',' busines,',' busynes,'),' business,'),((' bisynesse.',' busines.'),' business.'),((' businesse:',),' business:'),
                ((' biggeris',),' buyers'),((' byer',),' buyer'),((' buyeth',' byeth',' bieth'),' buyeth/buys'),
                    ((' bie ',),' buy '),((' bie;',),' buy;'),
            (('Bvt',),'But'),
                ((' boteler ',' butlar '),' butler '),
                ((' botere.',),' butter.'), ((' buttockes',),' buttocks'), ((' bottons',),' buttons'),
        (('Bi ',),'By '),((' bi ',),' by '),
    ((' cabines',),' cabins'),((' kab ',),' cab '),
            ((' calamitie ',),' calamity '),((' calamitie,',),' calamity,'),((' calamitie.',),' calamity.'),((' calamitie:',),' calamity:'),
                ((' calendis',),' calendars'),
                (('Calues',),'Calves'),((' calues',' caluys'),' calves'), (('Calfe',),'Calf'),((' calfe',),' calf'),
                (('callest','clepidist'),'callest/call'),((' clepiden',' clepide',' clepid',' clepun',' calledst',' calldest'),' called'),(('calleth','clepith'),'calleth/calls'),((' callinge',' callynge',' callyng'),' calling'), (('Clepe ','Cal '),'Call '),((' clepen ',' clepe ',' calle ',' cal '),' call '),((' clepe,',),' call,'),
                ((' calme,',),' calm,'),((' calme.',),' calm.'),((' calme:',),' calm:'),
            ((' cam ',' camen ',' comen '),' came '),((' cam,',' camen,'),' came,'),((' cam.',),' came.'),
                (('Camell',),'Camel'),((' camell',' camele'),' camel'),
                ((' campes',),' camps'),(('Campe',),'Camp'), ((' campe ',),' camp '),((' campe,',),' camp,'),((' campe.',),' camp.'),((' campe:',),' camp:'),
            ((' canst ',' canste '),' canst/can '),((' kunne ',' kan ',' ca '),' can '),
                (('Chanaanites','Cananites'),'Canaanites'),
                (('candlestickes','candelstickes','candelstyckes','candlestyckes','candilstikis'),'candlesticks'), (('Candlesticke',),'Candlestick'),(('candilstike','candelsticke','candlesticke'),'candlestick'),
                    ((' candell',' candel'),' candle'),#((' candell ',),' candle '),((' cadle,',),' candle,'),((' candell:',),' candle:'),
            (('Captaine','Captayne'),'Captain'),((' captaine',' captayne',' captayn'),' captain'),(('(captaine',),'(captain'),
                (('captiuitie ','captiuyte ','captiuity ','captyuite ','captyuyte ','caitiftee ','caitifte '),'captivity '),(('captiuitie,','captiuity,','captiuyte,','captyuyte,','caitiftee,','caitifte,','caytifte,'),'captivity,'),(('captiuitie.','captiuite.','captiuyte.','caitiftee.','caitifte.'),'captivity.'),(('captiuitie:','captiuyte:'),'captivity:'),(('caytifte;','caitifte;'),'captivity;'),
                    (('captiues',),'captives'),(('captyue','captiue','caitif'),'captive'),
            ((' carkeises',' carcases',' carkases'),' carcasses'),((' carcaise ',' carkasse ',' carcasse ',' carkeise ',' carkeis ',' carcase '),' carcass '),
                ((' carefull ',),' careful '),((' carefull,',),' careful,'), (('carelessely','carelesly'),'carelessly'),(('carelesse ',),'careless '),
                ((' carnall ',),' carnal '),
                (('carpeter',),'carpenter'),
                ((' carieth',' caried',' caryed'),' carried'),((' carrieth',' caryeth'),' carrieth/carries'),((' carienge',' carying'),' carrying'), (('Carie ','Cary '),'Carry '),((' carrie ',' carie ',' cary '),' carry '),
                ((' carued',),' carved'),((' caruing',),' carving'),((' carue ',),' carve '),
            ((' caas.',),' case.'),
                ((' casteth',' castith'),' casteth/casts/throws'), ((' castynge',' castyng',' castinge'),' casting/throwing'),((' castiden ',' kesten '),' cast/throw '),((' castedst ',' castidist ',' castide ',' caste ',' keste '),' cast/threw '),
                (('casteles','castels'),'castles'),((' castell',' castel'),' castle'),
            (('Catche ',),'Catch '),(('catche ',),'catch '),
                (('catterpiller','caterpiller','catirpiller'),'caterpillar'),
((' catels',),' chattels'), # Tob 1:19 Must go above 'cattle'
                ((' cattaile',' cattell',' catell',' cattel',' catel'),' cattle'),
            ((' caughte ',),' caught '), ((' caldron',' caudron',' cawdrun'),' cauldron'), ((' calker',),' caulker'), ((' causedst',),' caused'),
            ((' caues ',),' caves '),((' caues,',),' caves,'), ((' caue ',),' cave '),((' caue,',),' cave,'),((' caue.',),' cave.'),((' caue:',),' cave:'),
        ((' ceessiden',' ceesside',' ceessid',' ceassed'),' ceased'),((' ceaseth',' ceasseth',' ceesith'),' ceaseth/ceases'), (('Ceese ',),'Cease '),((' ceesse ',' ceasse '),' cease '),((' ceesse,',' ceasse,'),' cease,'),((' ceasse.',' ceesse.'),' cease.'),((' ceasse:',),' cease:'),
            (('Cedris',),'Cedars'),((' cedris',),' cedars'), (('Ceder','Cedre'),'Cedar'),((' cedre ',),' cedar '),((' cedre.',),' cedar.'),((' cedre?',),' cedar?'),((' cedre;',),' cedar;'),
            ((' cieling',' seelinge',' sieling',' sylinge'),' ceiling'),
            ((' celer;',),' cellar;'),
            (('centurioun','centurien'),'centurion'),
            (('cerymonyes',),'ceremonies'),
                (('Certainely',),'Certainly'),((' certayne',' certeyn',' certein',' certaine',' certen'),' certain'), (('certifie ',),'certify '),
        (('chaffe',),'chaff'),
                (('chaynes','cheynes','chaines'),'chains'),((' chaine ',' cheyne ',' chayne '),' chain '),
                    (('chayeri','chaieri','chaier'),'chair'),
                (('Caldea',),'Chaldea'),(('Caldees','Caldeis'),'Chaldees'), (('chalengere',),'challenger'),(('chalengi','chalenge'),'challenge'),
                (('chaumbris','chaumbers','chambres','chabers'),'chambers/rooms'),(('chamber ','chaumber ','chaumbre ','chambre ','chabre '),'chamber/room '),((' chaumber,',' chamber,'),' chamber/room,'),((' chambre.',),' chamber/room.'),((' chaumber:',' chambre:'),' chamber/room:'),
                (('chaunced','chaunsed'),'chanced'),(('chaunce ',),'chance '), (('Chancellour',),'Chancellor'),(('chanceler',),'chancellor'),
                    (('chaungide','chaungid','chaunged'),'changed'),(('changeth','chaungith'),'changeth/changes'), (('chaungeris',),'changers'), (('chaunginge','chaungynge','chaungyng','chaunging'),'changing'),((' chaunge ',),' change '),
                    ((' chanel',),' channel'),
                    ((' chaunt ',),' chant '),
                (('Chappell',),'Chapel'),((' chappell',' chappel'),' chapel'), ((' chapiters',),' chapters/capitals'),((' chapiter',),' chapter/capital'),
                ((' chargide',' chargid'),' charged'),
                    (('chearettes','charrettes','charettes','charrets','charets','charis'),'chariots'),((' charyot ',' charet ',),' chariot '),((' charet,',),' chariot,'),((' charet.',' chare.'),' chariot.'),((' charet:',),' chariot:'),((' charet;',),' chariot;'), (('charitie','charite'),'charity'),
                    (('charmeris',),'(snake-)charmers'),(('charmynge',),'charming'),
                (('chastiside','chastisid'),'chastised'), (('chastisynge',),'chastising'), (('chastened',),'chastened/rebuked'),(('chastens','chastisith','chasteneth'),'chastens/rebukes'),(('chastening','chastenynge','chastenyng'),'chastening/rebuking'), (('chastice ',),'chastise '),
                (('chatred',),'chattered'),
            ((' cheekis',' chekis'),' cheeks'),((' cheeke',' cheke'),' cheek'), #((' cheeke,',' cheke,'),' cheek,'),((' cheeke.',' cheke.'),' cheek.'),
                ((' cheare ',' chere '),' cheer '),((' cheere,',' cheare,'),' cheer,'), (('cheerefully',),'cheerfully'),(('cheerefull ','chearefull ','chearful '),'cheerful '),(('cheerefull,','chearefull,','cherefull,','cheareful,'),'cheerful,'),
                (('Cherubims','Cherubins'),'Cherubims/winged_creatures'),(('cherubims','cherubyms','cherubyns'),'cherubims/winged_creatures'),(('cherubim ','cherubym '),'cherubim/winged_creature '),
                (('chessenut','chesnut'),'chestnut'), ((' chestes',),' chests'),
                (('chewiden',),'chewed'),(('cheweth','chaweth'),'cheweth/chews'), (('chewe.','chawe.'),'chew.'),
            ((' chidden',),' chided/disputed/scolded'),((' chyde',),' chide'), # Lam 4:15, Mrk 8:32
                ((' chefest',),' chiefest'),(('chiefely',),'chiefly'),((' chiefe ',' chefe '),' chief '),((' chiefe,',),' chief,'), # Protect 'chiefest'
                (('childberyng',),'childbearing'),
                    (('childehode','childehood','chyldhood','childhode','childhod','childhed'),'childhood'),
                    (('childyshnesse','childishnesse'),'childishness'), (('childische',),'childish'),
                    (('childlesse',),'childless'),
                    (('childrens','chyldrens','childres'),'children’s'),(('chyldren',),'children'),(('childre ','chyldre '),'children '),(('childre,',),'children,'),(('childre.',),'children.'),(('childre:',),'children:'),
                    (('childes','chyldres'),'child’s'), (('childe','chylde'),'child'), #(('childe ','chylde '),'child '),(('chylde,','childe,'),'child,'),(('chylde.','childe.'),'child.'),(('childe:',),'child:'),
                (('chymney','chymenei'),'chimney'),
                (('chinkes',),'chinks'),
                (('chyualrie',),'chivalry'),
            ((' choocke',),' choke'),
                (('Chese ','Chuse '),'Choose '),((' chese ',' chuse '),' choose '),((' chuse,',),' choose,'),((' chuse.',),' choose.'), (('chesiden','chosun'),'chosen'),
                ((' chees',),' chose'), #((' chees ',),' chose '),((' chees,',),' chose,'),((' chees.',),' chose.'),
            ((' cristen',),' Christian'), (('Cristis',),'Christs'),(('Christes',),'Christ’s'),(('Christe','Crist'),'Christ'), (('Cronicles',),'Chronicles'),(('cronyclis',),'chronicles'),
            (('chirchis',),'churches'),(('chirche',),'church'),(('Churche ',),'Church '),(('Churche,',),'Church,'),
        ((' cerclis',),' circles'),((' sercle',),' circle'), ((' circuites',),' circuits'),((' circuite ',),' circuit '),
                (('circumcisioun','circucision'),'circumcision'),
            ((' cisterne',' cesterne'),' cistern'),
            (('citeseyns','citezins','citesyns'),'citizens'), (('Citie ',),'City '),(('Citie,',),'City,'),((' citees',' cytees',' cyties'),' cities'),((' cyte ',' citie ',' citee '),' city '),((' citie,',' citee,',' cite,'),' city,'),((' citie.',' citee.',' cite.'),' city.'),((' citie?',' citee?',' cite?'),' city?'),((' citie:',' citee:',' cite:'),' city:'),((' citie;',' citee;',' cite;'),' city;'),((' citie)',),' city)'),
        ((' claymed',),' claimed'),
                ((' clapt ',),' clapped '),((' clappe ',),' clap '),
                ((' claue ',),' clave '),
                ((' clawe',),' claw'),#((' clawes',),' claws'),
                ((' claye ',' cley '),' clay '),((' clei,',' cley,',' claye,'),' clay,'),((' claye.',),' clay.'),((' claye?',' clei?'),' clay?'),((' claye:',),' clay:'),
            ((' clenli',),' cleanly'), ((' cleannesse ',' cleannes ',' clenesse '),' cleanness '), (('clensiden','clensed','clensid','clensyd'),'cleansed'),(('clensyng','clensing'),'cleansing'),((' clense',),' cleanse'), ((' cleane ',' cleene ',' clene '),' clean '),((' cleane,',' cleene,',' clene,'),' clean,'),((' cleane.',' cleene.',' clene.'),' clean.'),((' cleane?',' clene?'),' clean?'),((' cleane:',' clene:'),' clean:'),((' cleene;',),' clean;'),
                    ((' clerere',),' clearer'),((' clearely',' cleerli',' clerly'),' clearly'), ((' cleare ',' cleer ',' clere '),' clear '),((' cleare,',),' clear,'),((' cleer.',),' clear.'),((' cleare?',),' clear?'),((' cleare:',),' clear:'),
                    ((' cleaued',' cleuyde',' cleued'),' cleaved/clung'),((' cleaveth',' cleaueth',' cleueth'),' cleaveth/cleaves_or_clings'),((' cleave ',' cleaue ',' cleue '),' cleave_or_cling '),
                ((' cleftes',),' clefts'),
            (('climbeth','clymmeth','clymeth','climeth'),'climbeth/climbs'), ((' clymme ',' clymbe ',' climbe ',' clime '),' climb '),
            ((' clyppers',),' clippers'),((' clippid',' clypped'),' clipped'),
            ((' cloake',' clooke',' cloke'),' cloak'),
                ((' cloddes',),' clods'),
                ((' closide',' closid'),' closed'),
                (('clothide','cloathed','clothid'),'clothed'), ((' clothinge',' clothyng'),' clothing'), (('cloothis','clothis','cloathes'),'clothes'),((' cloutes',),' cloths'),((' clooth',),' cloth'),
                ((' cloudie',),' cloudy'), ((' clowde',' cloudi',' cloude'),' cloud'), #((' cloudis',' cloudes'),' clouds'),((' cloude ',' clowde '),' cloud '),((' cloude,',),' cloud,'),((' cloude:',),' cloud:'),
                    ((' clouen',),' cloven'),
            ((' clustris',),' clusters'),
        ((' coales',' coolis',' coles'),' coals'),((' cole ',),' coal '),((' cole:',),' coal:'),
                ((' coostis',' coastes',' coostes',' coostos',' costes'),' coasts'), ((' coost',),' coast'),
                ((' cootis',' coottes',' coates',' cotes'),' coats'),((' cote ',),' coat '),((' coate,',' cote,'),' coat,'),
            ((' cockis',),' cocks'),((' cocke ',' cok '),' cock '),
            ((' coffyn',),' coffin'),
            ((' coold ',' colde '),' cold '),((' coold;',),' cold;'),
                ((' coler ',),' collar '),((' colledge',),' college'),
                ((' colouris',),' colours'),((' coloure ',),' colour '),
                ((' coolte',' colte'),' colt'),
            ((' commers',),' comers'), (('Comest ','Commest '),'Comest/Come '),((' comest ',' commest '),' comest/come '),((' comest,',' commest,'),' comest/come,'),
                    (('Commeth ',),'Cometh/Comes '),((' cometh',' cōmeth',' commeth'),' cometh/comes'),
                ((' commynge',' comynge',' commyng',' commyge',' comming',' cominge',' comyng',' comen'),' coming'),((' comun ',),' coming '), ((' comun,',),' come,'),((' comun;',),' come;'), # ((' comon ',),' come '),
                ((' conforted',' coforted',' coumfortide',' coumfortid'),' comforted'),((' comforteth',' coumfortith'),' comforteth/comforts'),((' coumfortour',' coforter'),' comforter'),(('coumfortynge',),'comforting'), ((' cofortles ',),' comfortless '), (('Comforte ','Coumfort ','Coforte '),'Comfort '),((' coumforten ',' coumforte ',' comforte ',' coumfort ',' coforte '),' comfort '),((' comforte,',' comforth,',' coumfort,',' conforte,'),' comfort,'),((' comforte.',),' comfort.'),((' comforte:',' conforte:'),' comfort:'),
                    (('Commaundement','Commandement'),'Commandment'),(('commaundemeutes','commaundementes','comaundementis','commandementes','commandements','commandmentes','commaudemetes','commaundemetes','comaundementes','comaundemetes','comaudementes'),'commandments'),(('commaudement','commaundement','comaundement','commandement','commadement','commaundemet','comandement','comaundemet'),'commandment'),
                            (('comaundidist','commaundedst','comaundedst','comaundiden','comaundyde','comaundide','comaundid','commaunded','comaunded','commauded','comanded'),'commanded'),(('commandeth','commaundeth','comaundith','comaundeth','comaudeth'),'commandeth/commands'),((' comaundynge',' comaundyng'),' commanding'),
                                (('Commaunde','Comaunde'),'Command'),((' commaunde ',' commande ',' comaunde ',' commaude ',' commaund ',' comaude '),' command '),((' commaunde,',' commande,',' comaunde,',' commaund,'),' command,'),
                        ((' commende ',),' commend '),
                        (('commytted','comytted'),'committed'),(('committeth','comitteth'),'committeth/commits'), (('Comitte ',),'Commit '),((' committe ',' comitte '),' commit '),((' comit',),' commit'),
                        ((' commoditie ',),' commodity '),
                            (('COMMONLI',),'COMMONLY'),((' comynli',),' commonly'), ((' comyn',' comon'),' common'),
                                (('commoned','comoned'),'communed'), (('communicacion','comunicacion'),'communication'),
                (('companyon',),'companion'), (('cumpenyes','cumpanyes','companyes'),'companies'),((' companye',' cumpenye',' cumpany',' cumpeny'),' company'),((' companie ',),' company '),((' companie.',),' company.'),((' companie:',),' company:'),((' cumpany;',),' company;'),
                    ((' coparable',),' comparable'), (('comparisoun','comparyson','compareson'),'comparison'), ((' copared',),' compared'), ((' copare',),' compare'),
                    ((' compassed',' cumpassiden',' cumpasside',' cumpassid',' compased',' copassed',' copased'),' compassed/surrounded'),((' cumpassen',),' compassing/surrounding'),((' compasseth',' copaseth'),' compasseth/compasses/surrounds'),((' compass ',' compasse ',' cumpasse ',' compase ',' cumpass ',' cumpas ',' copase '),' compass/all_around '),((' compass,',' compasse,',' cumpas,'),' compass/all_around,'),((' compass.',' cumpas.',),' compass/all_around.'),((' compass;',' cumpas;',),' compass/all_around;'), # Joel 3:11-12
                        (('compassioun','copassion'),'compassion'),(('compassio ',),'compassion '),
                    ((' compell ',),' compel '),
                    ((' compyle ',),' compile '),
                    (('complaynte','complaynt','coplaynte'),'complaint'),((' complayned',' coplayned'),' complained'),(('complaynynge',),'complaining'),((' complaine,',),' complain,'),((' coplayne.',),' complain.'),((' complayne:',),' complain:'),
                    (('comprehendiden',),'comprehended'), (('comprehende ','comprehede '),'comprehend '),
                    (('compunccioun',),'compunction'),
            (('conceiled',),'concealed'),((' conceale ',),' conceal '),
                    ((' conceipt',),' conceit'),((' conceate,',),' conceit,'),
                        (('conseyueden','conceyuede','conseyuede','conseyued','conceaued','conceiued','couceiued','coceiued'),'conceived'), (('conseyuyng',),'conceiving'), (('conseyue','conceiue','coceaue'),'conceive'),
                    ((' concernynge',' concernyng',' cocernynge',' cocerning'),' concerning'),((' concerne ',),' concern '),
                    ((' conclucion',),' conclusion'),
                    (('concubins',),'concubines'),(('concubyne',),'concubine'),
                (('condempned','codempned'),'condemned'),((' condempne ',' condemne ',' condenme '),' condemn '),
                    ((' condicioun',),' condition'),
                    ((' conduites',),' conduits'),
                ((' confederacie ',),' confederacy '), ((' cofederate ',),' confederate '),
                    ((' conferre ',),' confer '),
                        (('cofessing','confessynge','confessyng'),'confessing'), (('confessioun',),'confession'),(('Confesse',),'Confess'),((' confesse ',' cofesse '),' confess '),((' confesse,',),' confess,'),((' confesse.',),' confess.'),((' confesse:',),' confess:'),
                    (('confydence','cofidence'),'confidence'),
                        (('confermyde','confermede','confermyd','confermed'),'confirmed'),(('confirmyng',),'confirming'),((' confirme ',' conferme '),' confirm '),
                    (('cofounded','confouded'),'confounded'), ((' confounde ',' cofounde '),' confound '),
                    (('Confusioun',),'Confusion'),((' confusioun',' confucion',' cofusion',' cofucion',' confucio'),' confusion'),
                (('congregacions','cogregacios'),'congregations'),(('congregacioun','congregacion','cogregacion','congregacon'),'congregation'),
                (('coniurer',),'conjurer'),
                ((' conquere ',),' conquer '),
                (('consentest','consentedst'),'consentest/consent'), ((' consente ',),' consent '),
                    (('considred','consydred','cosidered','cosidred'),'considered'),(('considereth','cosidereth','considreth'),'considereth/considers'),(('considerest','consyderest'),'considerest/consider'), (('Considre ','Cosidre '),'Consider '),((' considre ',' cosider ',' cosidre '),' consider '),((' considre,',),' consider,'),((' considre?',),' consider?'),
                    (('consolacion',),'consolation'),
                    (('conspiracie ',),'conspiracy '), ((' conspirid',),' conspired'),((' conspyre',),' conspire'),
                    (('constitucioun',),'constitution'), ((' constrayned',' constreynede',' constreinede',' costrayned'),' constrained'),((' constreyne ',),' constrain '),
                    ((' cosumed',),' consumed'),((' consumynge',' consumyng'),' consuming'), (('Cosume ',),'Consume '),((' cosume ',),' consume '),
                (('conteined','conteyned'),'contained'),(('conteine ','containe ','contayne '),'contain '),
                    ((' contemn ',' contemne '),' contemn/treat_with_contempt '),
                        ((' contet ',),' content '),
                    (('contynueli',),'continually'),(('continuall ','contynuel '),'continual '),
                        (('contynuede','contynued'),'continued'),(('continueth','cotinueth'),'continueth/continues'),(('contynuynge','contynuen'),'continuing'),(('contynue','cotynue','cotinue'),'continue'),
                    ((' contrarie',' cotrary'),' contrary'),((' contrit ',' cotrite '),' contrite '), (('controuersie',),'controversy'),
                (('conueniently','coueniently','couenabli'),'conveniently'), (('conuenient','couenable'),'convenient'),
                    ((' conuersaunt',),' conversant'),
                    ((' conuer',),' conver'), ((' convertid',),' converted'), ((' conversis',),' converts/proselytes'), ((' converten ',' converte ',' couerte '),' convert '),((' converte,',),' convert,'), #((' conuersation',),' conversation'), ((' conuerting',),' converting'),
                    ((' conuey',),' convey'),
                ((' conuocation',' couocation',' couocacion'),' convocation'),
            ((' cookes',),' cooks'),
            (('Corall',),'Coral'),((' corall',),' coral'), ((' coarde',' coard',' corde'),' cord'), #((' coardes',' cordes'),' cords'), ((' coorde,',),' cord,'),((' coard',),' cord'),
                (('Corinthyans',),'Corinthians'),
                (('Corne ',),'Corn '),((' corne ',),' corn '),((' corne,',),' corn,'),((' corne.',),' corn.'),((' corne?',),' corn?'),((' corne:',),' corn:'),((' corne;',),' corn;'),  ((' cornerid',),' cornered'),
                ((' correccion',),' correction'),
                    ((' corrupcion',),' corruption'),((' corruptnes.',),' corruptness/corruption.'), (('Corrupte ',),'Corrupt '),((' corrupte ',),' corrupt '),((' corrupte,',),' corrupt,'),((' corrupte.',),' corrupt.'),
            ((' costis',),' costs'),
            ((' coutche ',' couche '),' couch '),((' couche.',),' couch.'),
                 ((' Couldest',),' Couldest/Could'),((' couldest',),' couldest/could'), ((' coulde ',' coude '),' could '),
                ((' cuppled',),' coupled'),
                ((' councelide',),' counselled'),(('Counseller',),'Counsellor'),((' counsellour',' counselour',' counseller',' counceler'),' counsellor'),
                        ((' counsayles',' councels'),' councils/counsels'), (('Councill ',),'Council '),(('Councill,',),'Council,'),((' counsell ',' counsel ',' councill ',' councell ',' councel '),' council/counsel '),((' counsel,',' counsell,',' coucel,'),' council/counsel,'),((' counsell.',' councell.'),' council/counsel.'),((' counsell:',' counsel:',' counsayle:'),' council/counsel:'),((' counsell;',),' council/counsel;'),
                    ((' couted',),' counted'),((' counte ',),' count '),
                        (('countenaunce','countenauce','coutenauce'),'countenance'),
                        ((' countreyes',' countreies',' countreys',' countreis',' cuntreis',' countrees',' coutrees',' cuntrees',' countres'),' countries'),((' cuntree',' countrey',' cuntrey',' cuntrei',' countre',' cuntre',' coutre'),' country'),((' countrie,',),' country,'),
                ((' couragious',),' courageous'), ((' corage ',),' courage '),((' corage.',),' courage.'),
                    ((' courtes',),' courts'), ((' courte ',),' court '),((' courte.',),' court.'),((' courte:',),' court:'),
            (('Couenant',),'Covenant'),((' couenannt',' couenaunt',' couenaut',' couenant'),' covenant'),
                ((' couerdest',' couered'),' covered'), ((' covereth',' couereth',),' covereth/covers'),((' coverest',' couerest',),' coverest/cover'), ((' coueringe',' couerynge',' couering'),' covering'), (('Couer',),'Cover'),((' couer',),' cover'),
                    ((' couert',),' covert'),
                (('couetousnesse','coueteousnes','coueitise','couetousnes','cuvetousnes','coveteousnes'),'covetousness'),((' couetous',' coueytise'),' covetous'), ((' coueitide',' coueted'),' coveted'),((' coveteth',' coueitith',' coueteth'),' coveteth/covets'), ((' coueyte ',),' covet '),((' couet',),' covet'), # (('cuvetousnes.',),'covetousness.'),
            ((' kowe ',' kow '),' cow '),((' cowe,',),' cow,'),((' cowe.',),' cow.'),
        (('cradels',),'cradles'),
                (('craftesmen',),'craftsmen'),(('craftesman',),'craftsman'), (('craftely',),'craftily'), (('craftie ','crafti '),'crafty '), ((' crafte ',),' craft '),
                ((' crasheth',' crassheth'),' crasheth/crashes'),
                ((' craued',),' craved'),
            (('Creatour',),'Creator'),(('creatour',),'creator'), ((' creacion',),' creation'),
                (('creditour',),'creditor'),
                (('creepeth','creepith','crepeth','crepith'),'creepeth/creeps'),(('crepynge','crepinge'),'creeping'),(('creepe ',),'creep '),(('creepe,',),'creep,'),(('creepe:',),'creep:'),
            ((' crieden',' criede',' cryed'),' cried'),
                (('crimosin','crimsin'),'crimson'),
                (('crepell',),'crippled'),
            ((' crokid',' croked'),' crooked'), (('Crosse',),'Cross'),((' crosse ',' cros '),' cross '),((' crosse,',' cros,'),' cross,'),((' crosse.',),' cross.'),
                ((' crowe ',),' crow '),((' crowe.',),' crow.'),
                (('corouned','corowned','crownede'),'crowned'),(('crownes','crounes'),'crowns'),(('Crowne',),'Crown'),(('croune ','crowne ',),'crown '),(('crowne,',),'crown,'),(('coroun',),'crown'),
            ((' crieth',' cryeth'),' crieth/cries'),((' criynge',' crienge',' criyng'),' crying'),(('Crye ','Crie '),'Cry '),((' crye ',' crie '),' cry '),((' crye,',' crie,'),' cry,'),((' crie.',),' cry.'),((' crie?',' crye?'),' cry?'),((' crie:',),' cry:'),((' crie;',),' cry;'),
                ((' Christall',' christall',' chrystall'),' crystal'),
            ((' crucifien',' crucifed'),' crucified'),((' crucifie ',),' crucify '),
                (('Crueltie ',),'Cruelty '),((' crueltie ',' cruelte '),' cruelty '),((' crueltie,',),' cruelty,'),((' crueltie.',),' cruelty.'),((' cruell ',),' cruel '),((' cruell,',),' cruel,'),((' cruell.',),' cruel.'),
                ((' crumbe',' crumme',' cromme',' crome'),' crumb'),
        ((' cubytes',' cubites',' cubitis'),' cubits'),((' cubite ',),' cubit '),((' cubite,',),' cubit,'),((' cubite.',),' cubit.'),
            ((' kunnyng',' connynge',' cunnyng'),' cunning'),
            ((' cuppis',' cuppe',),' cup'),
            ((' keuered',),' cured'),
                (('Cursid',),'Cursed'),((' cursedest',' cursedst',' cursidist',' cursiden',' curside',' cursid'),' cursed'),((' curseth',' cursseth',' cursith'),' curseth/curses'),((' cursyngi',' cursynge',),' cursing'),
                ((' curtayne',' curtaine'),' curtain'),
            ((' cuschen',),' cushion'),
                ((' customes',),' customs'),((' custome ',),' custom '),((' custum',),' custom'),((' custome,',),' custom,'),
            ((' cutteth',' kittith'),' cutteth/cuts'),((' cutt ',' kitte '),' cut '),
        (('Cymbales',),'Cymbals'),((' cymbales',' cymbalis'),' cymbals'),
            (('Cypresse','Cipresse'),'Cypress'),((' cipresse',),' cypress'),
    ((' dayly',' daylie'),' daily'),
            (('dammage',),'damage'),
                (('dampnacioun','dampnacion','dampnation','damnacion'),'damnation'),(('dampnatio.',),'damnation.'),
                (('dampned',),'dampened'),
                ((' damselles',' damosels',' damesels'),' damsels'), (('Damosell','Damysel'),'Damsel'),((' damisele',' damysele',' damosell',' damosel',' damesel',' damsell',' dasell',' damysel'),' damsel'),
            ((' daunsers',),' dancers'), ((' danceth',' daunseth'),' danceth/dances'),((' daunside',' daused'),' danced'),((' dauncing',' daunsing'),' dancing'),((' daunse',' daunce',' dauce'),' dance'),
                ((' daunger',' dauger'),' danger'),
            (('darckened','darkned'),'darkened'),((' darcke ',' darke ',' derke ',' derk '),' dark '),((' darcke,',' darke,',' derk,'),' dark,'),((' darke.',' derk.'),' dark.'),((' darke?',),' dark?'),((' darke:',),' dark:'),((' darke;',),' dark;'),
                    (('darcknes ','darkenes ','darknes ','dercknes '),'darkness '),(('darkenes,','darcknes,'),'darkness,'),(('darkenes.',),'darkness.'),(('darkenes:','darknes:'),'darkness:'),(('darcknesse','derknesse','derknessis','darkenesse','darknesse'),'darkness'),
                ((' derlingi',' dearlyng',' dearlinge',' dearling',' derlynge',' derlyng',' derlinge',' derling'),' darling'),
                ((' dartes',' dartis'),' darts'),((' darte ',),' dart '),
            ((' dasshed',),' dashed'),
            (('douytris',),'daughters'), (('Doughter','Douytir'),'Daughter'),(('daugther','douyter','douytir','doughter'),'daughter'),
            (('Dauith','Dauid','Dauyd'),'David'),(('Davids',),'David’s'),
            (('dawnynge','daunynge','dawnyng'),'dawning'),
            ((' daies',' dayes',' dais',' daes'),' days'), (('Daye ','Dai '),'Day '),((' daye ',' daie ',' dai '),' day '),((' daye,',' daie,',' dai,'),' day,'),((' daye.',' daie.',' dai.'),' day.'),((' daye?',' dai?'),' day?'),((' daye:',' daie:',' dai:'),' day:'),((' dai;',),' day;'),
        ((' dekene',),' deacon'),
                ((' deedly',' dedly'),' deadly'),
                ((' deafe ',' deffe ',' deef '),' deaf '),((' deafe,',),' deaf,'),((' deafe.',),' deaf.'),((' deef;',),' deaf;'),((' deafe:',),' deaf:'),
                ((' dealynge',' dealyng',' dealinge'),' dealing'), ((' dealte ',' delt '),' dealt '), ((' deales',),' deals'), (('Deale ',),'Deal '),((' deale ',),' deal '),((' deale,',),' deal,'),
                ((' dearely',),' dearly'), (('Deare ',),'Dear '),((' deare ',' dere '),' dear '),
                ((' deathes',),' deaths'),((' deeth',' deth',' derth'),' death'),
            ((' dettouri',' dettour',' detter',' debter'),' debtor'), ((' dettes',' dettis'),' debts'),((' dett ',),' debt '),
            ((' decaye ',),' decay '),((' decaye.',),' decay.'),((' decaye:',),' decay:'),
                (('deceytfulness',),'deceitfulness'),(('disseytfulnes ','disceatfulnes ','deceitfulnes '),'deceitfulness '),
                        (('deceitfull ','disceatfull ','disceatful ','deceytfull ','deceiptfull '),'deceitful '),(('deceitfull.',),'deceitful.'),(('disceatfull:',),'deceitful:'), ((' deceite',' deceipt',' disceate',' disceipt',' disseit',' diceyte'),' deceit'),
                    (('disseyueden',),'deceived'),(('disseyuede',),'deceived_or_dissuaded'),((' disseyued',),' deceived'),
                        (('deceiveth','deceiueth','disceaueth','disseyueth'),'deceiveth/deceives'),(('disseyve','disceaue','deceave','deceiue','deceaue','disseyue'),'deceive'),
                (('discided',),'decided'),
                ((' decte ',' dect '),' decked '),((' deckynge',),' decking'),((' decke ',),' deck '),
                ((' decre ',),' decree '),
            ((' dedicacion',),' dedication'),
            ((' deedes',' dedes',' dedis'),' deeds'),((' deede ',' dede '),' deed '),((' deede,',' dede,'),' deed,'), #((' demed.',),' deemed.'),
                ((' deepenes',' depnesse'),' deepness'), ((' deepes ',),' deeps/depths '),((' deepes,',),' deeps/depths,'),((' deeps.',' deepes.',' depes.'),' deeps/depths.'),((' deeps:',),' deeps/depths:'), ((' deepely',' depely',' deepli'),' deeply'),
                    (('Deepe ',),'Deep '),((' deepe ',' depe '),' deep '),((' deepe,',' depe,'),' deep,'),((' deepe.',' depe.'),' deep.'),((' deepe:',' depe:'),' deep:'),((' deepe;',),' deep;'),
                (('Deere,',),'Deer,'),
            ((' defeate ',),' defeat '),
                (('defendere',),'defender'), (('defendide','defendid'),'defended'),(('defendeth','defendith'),'defendeth/defends'), (('Defende ',),'Defend '),((' defende ',),' defend '),
                ((' deferrid',),' deferred'),((' deferre ',),' defer '),
                ((' defouliden',' defoulide',' defoulid'),' defiled'),((' defileth',' defyleth',' defoulith'),' defileth/defiles'),((' defoulen',),' defiling'),((' defyle',' defoule'),' defile'), # includes defyled, defyles
                ((' defieth',' defyeth'),' defieth/defies'),
                ((' defraude ',),' defraud '),
                ((' defie ',),' defy '),((' defie,',),' defy,'),
            ((' degre ',),' degree '),
            ((' delaied',),' delayed'),((' delayes',),' delays'),
                ((' delicatelye',' delicatly'),' delicately'),
                    ((' delitiden',' delitide',' delited',' delyted'),' delighted'), ((' delightest',' delytest',' delitest'),' delightest/delight'),((' delighteth',' delyghteth',' delyteth',' deliteth'),' delighteth/delights'), ((' delites',),' delights'), (('Delite ','Delyte '),'Delight '),((' delyght ',' delyte ',' delite '),' delight '),((' delite,',),' delight,'),((' delyght.',' delyte.',' delite.'),' delight.'),((' delyght:',),' delight:'),
                (('delyueraunce','delyuerauce','deliueraunce','deliuerance','delyverauce'),'deliverance'), ((' delyuerer',' deliuerer'),' deliverer'),
                    (('deliueridist','delyueriden','delyueride','delyuerid','deliuered','delyuerede','delyuered','delyvered'),'delivered'),(('deliverest','delyuerest','deliuerest'),'deliverest/deliver'),(('delivereth','delyuereth','deliuereth'),'delivereth/delivers'), (('Deliuer ','Delyuere ','Delyuer '),'Deliver '),((' delyuere ',' diliuere ',' delyuer ',' deliuer '),' deliver '),((' delyuere.',),' deliver.'),((' delyuere?',),' deliver?'),((' deliuer',' delyuer',' delyvre'),' deliver'),
            ((' demaund',),' demand'),
            ((' dennys',),' dens'),((' denne',' deen'),' den'),
                ((' denydest',' denyede',' denyed'),' denied'), ((' denounse',),' denounce'), ((' denie ',' denye '),' deny '),
            ((' departiden',' departide',' departid'),' departed'),((' departynge',),' departing'),
                    (('Departe ',),'Depart '),((' departe ',),' depart '),((' departe,',),' depart,'),((' departe.',),' depart.'),
                ((' deprauyd',),' depraved'), ((' depriue',),' deprive'),
                ((' deapthes',' depthis',),' depths'), (('Depthe',),'Depth'),((' depthe',' deapth',' deepth'),' depth'),
                ((' deputie ',),' deputy '),
            (('descendinge',),'descending'),((' descende ',' descede '),' descend '),((' descende,',),' descend,'),
                    (('descripcion',),'description'),
                ((' deserte ',' desart '),' desert '),((' deserte,',),' desert,'),((' deserte.',),' desert.'),((' deserte?',),' desert?'),((' deserte:',),' desert:'),((' deseert',),' desert'),
                    ((' deserue',),' deserve'),
                ((' desireth',' desirith'),' desireth/desires'), ((' desiriden',' desiride',' disired',' desirid'),' desired'), ((' desiris',),' desires'),((' dissiren',),' desiring'),((' desyre',' desier'),' desire'),((' desijr ',' desir '),' desire '),
                (('desolacioun','desolacion'),'desolation'), ((' desolat ',),' desolate '),((' desolat,',),' desolate,'),((' desolat.',),' desolate.'),((' desolat;',),' desolate;'),
                ((' despaire ',' dispare '),' despair '),
                    ((' despisinge',' dispisyng',' dispising'),' despising'),((' dispisiden',' dispiseden',' dispiside',' disspisid',' despysed',' dispisid'),' despised'),((' despiseth',' dispisith'),' despiseth/despises'),((' dispisen',' despyse',' dispise'),' despise'),
                        ((' despitefull ',' dispitefull '),' despiteful '),((' despyte',),' despite'),
                ((' destroier',),' destroyer'), ((' destrieden',' distriede',' destriede',' destroied',' destried',' distried'),' destroyed'), (('destroyethe',),'destroyeth'),(('distriynge','distriyng','destrien','distrien'),'destroying'), (('Destroie ',),'Destroy '),((' distrie ',' destrie ',' destroye ',' distroye ',' distruye ',' destroie ',' destoy '),' destroy '),((' destroye,',' distrie,'),' destroy,'),
                    (('destruccios',),'destructions'),(('destruccion','distruction'),'destruction'),(('destruccio ',),'destruction '),
            ((' determyne',),' determine'),
            ((' deuyces',),' devices'),
                ((' deuelis',' devylles',' deuylles',' devvyls',' deuils',' deuyls',' deuels',' diuels',' devyls'),' devils'),((' devyll',' deuell',' deuyll',' devill',' deuill',' deuel'),' devil'),
                    ((' deuised',' deuysed'),' devised'), ((' deui',),' devi'),
                ((' deuoted',),' devoted'),
                    ((' deuouriden',' deuouride',' deuourid',' deuoured',' deuouryd'),' devoured'),((' devoureth',' deuoureth',' deuourith'),' devoureth/devours'),((' deuowrynge',' deuourynge',' deuouryng',' deuowren',' deuouren'),' devouring'),((' deuoure ',' devoure '),' devour '),((' deuoure,',),' devour,'), ((' deuour',),' devour'),
                        ((' deuout',),' devout'),
            ((' deawe ',' deaw ',' deew ',' dewe '),' dew '),((' deawe,',' dewe,'),' dew,'),((' dewe.',),' dew.'),
        (('Dyall ',),'Dial '),((' diall ',),' dial '), ((' diamonde',),' diamond'),
            (('Didst ','Diddest ',),'Didst/Did '),((' didst',' dyddest',' diddest',' didist',' dydst'),' didst/did'), (('Dyd ',),'Did '),((' dyd ',' diden ',' dide '),' did '),((' dide,',' dyd,'),' did,'),((' diden.',' dide.'),' did.'),((' dide?',),' did?'),((' dyd:',),' did:'),((' diden;',),' did;'),
            ((' dieth',' dyeth'),' dieth/dies'), ((' dieden ',' diede ',' dyed '),' died '),((' diede,',' dyed,'),' died,'),((' dyed.',),' died.'),((' diede;',),' died;'),((' diynge',' dien'),' dying'), ((' dye.',),' die.'),
            ((' diggest',' dyggest'),' diggest/dig'),((' diggeth',' dyggeth'),' diggeth/digs'),((' digyng',),' digging'), (('Digge ','Dygge '),'Dig '),((' digge ',),' dig '),
                ((' dignitie',' dignitye'),' dignity'),
            ((' diligentli',),' diligently'),((' diligente',),' diligent'),
            ((' dymme ',),' dim '),((' dymme,',' dimme,'),' dim,'),((' dimme.',),' dim.'),((' dymme?',' dimme?'),' dim?'),((' dimme!',),' dim!'),((' dimme:',),' dim:'),
            ((' dypte',' dipt'),' dipped'),((' dippeth',' dyppeth',' deppeth'),' dippeth/dips'),
            ((' dirtie ',),' dirty '),
            ((' disalowing',),' disallowing'),((' dispoynted',),' disappointed'),(('disappointeth','dispoynteth'),'disappointeth/disappoints'),
                ((' discerne ',),' discern '),((' discerne:',),' discern:'),
                    (('disciplis',),'disciples'),
                    (('discolourid',),'discoloured'), (('disconforted','discuforted'),'discomforted'),(('discoumfort',),'discomfort'),
                        (('discouer','dyscouer'),'discover'),
                    (('discreetely','discretly'),'discretely'),(('discrecion',),'discretion'),
                (('disdayned',),'disdained'),(('disdaine ',),'disdain '),(('disdayne',),'disdain'),
                ((' desease',' disese'),' disease'),
                ((' disshes',),' dishes'),((' dische ',),' dish '),((' disch,',),' dish,'),((' dissche.',' dysshe.',' disshe.'),' dish.'),
                    (('dishonor',),'dishonour'),(('dishonoure ',),'dishonour '),(('dishonoure,',),'dishonour,'),(('dishonoure.',),'dishonour.'),
                (('disinherite ',),'disinherit '),
                (('dismaied',),'dismayed'),
                ((' dishobedient',),' disobedient'), ((' disobeied',),' disobeyed'),
                (('dispatche ',),'dispatch '),
                    (('dispearsed',),'dispersed'),
                    (('displeaseth','displesith'),'displeaseth/displeases'),
                    (('disposeth','disposith'),'disposeth/disposes'),
                    (('disputacio?',),'disputation?'),((' disputiden',),' disputed'),(('dispuytynge','disputinge','disputynge','disputyng','disputen'),'disputing'), ((' dispuyte',),' dispute'),
                (('disquietnesse',),'disquietness'),(('disquietnes ',),'disquietness '),
                (('dissembleth','dyssembleth'),'dissembleth/dissembles'),
                ((' distresse ',),' distress '),((' distresse,',),' distress,'),((' distresse.',),' distress.'),((' distresse:',),' distress:'),
                    ((' disturblide',' disturblid'),' disturbed'),((' disturbeth',' disturblith'),' disturbeth/disturbs'),((' disturblyng',),' disturbing'),((' disturbest',' disturblist'),' disturbest/disturb'),
            ((' dychis',),' ditches'),
            ((' dyuerse ',' diverse ',' divers ',' dyvers ',' diuerse ',' diuers ',' dyuers '),' diverse/various '), ((' dyuersitee',' dyuersite'),' diversity'),
                (('devided','deuided','deuyded','devyded','diuided'),'divided'),(('Diuide ',),'Divide '),((' diuid',' devid',' deuyd'),' divid'),
                    ((' diuinatios',),' divinations'), ((' dyuynour',),' diviner'), ((' dyuynyd',),' divined'),((' dyuynyngi',),' divining'), ((' diuin',' devin',' dyuyn'),' divin'), # u is already changed to v at ' deui'
                    ((' devision',),' division'), ((' diuis',),' divis'),
                (('devorsement','deuorcemet','diuorcement'),'divorcement'), ((' diuorced',),' divorced'),
        ((' doere',),' doer'), (('Dost ','Doest '),'Dost/Do '), ((' doth',' doeth',' doith'),' doth/does'), (('Doe ',),'Do '),((' doe ',),' do '),((' doe,',),' do,'),((' doe.',),' do.'),((' doe?',),' do?'),((' doe:',),' do:'),
            (('doctryne','doctryn'),'doctrine'),
            ((' dogges',' doggis'),' dogs'),((' dogge ',' dogg '),' dog '),((' dogge,',' dogg,'),' dog,'),((' dogge.',),' dog.'),
            ((' doyngis',),' doings'),((' doinge',' doynge',' doyng',' doen'),' doing'),
            ((' dolefull ',),' doleful '),
            (('dominacion','domynacion'),'domination'),
            ((' doon ',' don '),' done '),((' doon,',' don,'),' done,'),((' doon.',' don.'),' done.'),((' doon;',),' done;'),
            ((' doores',' dores',' doris'),' doors'),((' doore',' dore'),' door'),
            ((' dost ',' doest ',' doist '),' dost/do '),((' doist;',),' dost/do;'),
            ((' doublid',),' doubled'),((' dubble',),' double'),
                ((' douteful,',),' doubtful,'), (('Doubtlesse',),'Doubtless'),((' doubtlesse',' doutlesse',' doutles'),' doubtless'), ((' douteth',),' doubteth/doubts'),((' doutide',),' doubted'), ((' doute ',),' doubt '),((' doute,',),' doubt,'),((' doute)',),' doubt)'),
                ((' dowe ',' dow '),' dough '),((' douy',),' dough'),((' dow,',),' dough,'),((' dow;',),' dough;'),
            (('Doue',),'Dove'),((' dowue',' doue'),' dove'),
            ((' downe ',' doune ',' doun '),' down '),((' downe,',' doun,'),' down,'),((' downe.',' doune.',' doun.'),' down.'),((' downe:',),' down:'),((' doun;',),' down;'),((' downe)',),' down)'), (('downewarde','downwarde','downeward','dounward'),'downward'),
        ((' draffis',),' drafts'),
                ((' dragge;',),' drag;'), ((' dragouns',' dragos'),' dragons'),((' dragoun',),' dragon'),
                ((' drammes',),' drams'),
                ((' dranke',),' drank'),
                ((' drawyng',),' drawing'), ((' drawun',' drawen'),' drawn'), (('Drawe ',),'Draw '),((' drawe ',),' draw '),((' drawe,',),' draw,'),
            (('dreadfull ','dreedful '),'dreadful '),(('dreadfull.',),'dreadful.'),(('dreadfull:',),'dreadful:'),(('dredeful;',),'dreadful;'),
                        (('dredden','dredde'),'dreaded'),(('dreadeth','dredith'),'dreadeth/dreads/fears'),(('dredynge','dredinge','dreden'),'dreading'),(('Dreade ','Drede '),'Dread '),(('drede ',),'dread '),(('drede,',),'dread,'),(('drede.',),'dread.'),(('drede;',),'dread;'),(('drede?',),'dread?'),
                    (('Dremes',),'Dreams'),(('dreames','dremes'),'dreams'), (('dremede',),'dreamed'),(('dreame ','dreem '),'dream '),(('dreame,','dreem,'),'dream,'),(('dreame.','dreem.'),'dream.'),(('dreame:',),'dream:'),(('dreem;',),'dream;'),
                ((' dregges',),' dregs'),
                ((' dresside',' dressid'),' dressed'),((' dresse ',),' dress '),
                ((' drewest',),' drewest/drew'),((' drewe ',' drowy ',' drue ',' drow '),' drew '),
            (('drinkest','drynkest'),'drinkest/drink'),(('drinketh','drynketh','drinkith'),'drinketh/drinks'),(('drynkynge','drynken'),'drinking'), (('Drinke',),'Drink'),((' dryncke ',' drynke ',' drynk ',' drincke ',' drinke '),' drink '),((' drincke,',' drinke,',' drynke,'),' drink,'),((' drinke.',' drynke.',' drike.'),' drink.'),((' drinke?',' drynke?'),' drink?'),((' drynke:',' drinke:'),' drink:'),((' drynke;',' drinke;'),' drink;'),
                ((' dryuun',),' driven'),((' driveth',' driueth'),' driveth/drives'), (('Driue','Dryue'),'Drive'),((' driu',' dryu'),' driv'),
            ((' droppinge',),' dropping'),((' droppes',),' drops'),((' droppe ',),' drop '),
                ((' dross ',' drosse '),' dross/slag '),((' dross,',' drosse,'),' dross/slag,'),((' dross:',' drosse:'),' dross/slag:'),
                ((' draue',' drave',' droue',' droof'),' drove'),
                ((' drouned',' dreynt'),' drowned'),((' drowne ',),' drown '),
            (('dronckarde','drunkarde'),'drunkard'), (('dronckennesse','dronckenesse','dronckennes','drunkennesse','drunkenesse'),'drunkenness'),(('drunkennes ',),'drunkenness '), ((' droncken ',),' drunken '), ((' dronken ',' druncke ',' drunke '),' drunk '),
            ((' drieden',' driede',' dryed'),' dried'),((' driest',' dryest'),' driest/dry'),((' drieth',' dryeth'),' drieth/dries'),(('dryenge','driyng'),'drying'), ((' drie ',' drye '),' dry '),((' drie,',' drye,'),' dry,'),((' drie.',' drye.'),' dry.'),
        ((' diggide',' digged',' dygged'),' dug'),
            ((' duykis',' duikis',' dukis'),' dukes'),((' duyk ',),' duke '),
            ((' doumb',' domme',' dumbe',' dumme'),' dumb'),
            ((' dongeon',),' dungeon'), ((' dongue',' doung',' donge'),' dung'),
            ((' duste ',),' dust '),
            ((' duetie ',),' duty '),
        (('dwellidist','dwelliden','dwellide','dwellyde','dwellid','dwelte'),'dwelled/dwelt'), (('dwelleris',),'dwellers'),(('dwellere ',),'dweller '), (('dwellest','dwellist'),'dwellest/dwell'),(('dwelleth','dwellith'),'dwelleth/dwells'),(('dwellynge','dwellyngi','dwellyng','dwellinge','dwellige'),'dwelling'), (('Dwelle ',),'Dwell '),((' dwellen ',' duellen ',' dwelle ',' dwel '),' dwell '),((' dwelle,',' dwel,'),' dwell,'),((' dwelle.',),' dwell.'),((' dwelle?',),' dwell?'),((' dwelle;',),' dwell;'),
    (('Ech ',),'Each '),((' eche ',' ech '),' each '),((' ech,',),' each,'),
            (('Aegles','Egles'),'Eagles'),((' eglis',),' eagles'), (('Aegle','Egle'),'Eagle'),((' egle ',),' eagle '),((' egle,',),' eagle,'),
            (('Eerli ',),'Early '),((' eerli',' earely',' earlie',' erly'),' early'),
                ((' eares',' eeris',' eris'),' ears'),#((' eares,',' eeris,'),' ears,'),((' eares.',' eeris.'),' ears.'),((' eares:',),' ears:'),((' eeris;',),' ears;'),
                    ((' eare ',' eere '),' ear '),((' eare,',' eere,'),' ear,'),((' eare.',' eere.'),' ear.'),((' eare:',),' ear:'),((' eare;',),' ear;'),((' eare)',),' ear)'),
                ((' erthene',' erthen',' erthun'),' earthen'), (('Erthe',),'Earth'),((' erthe',' erth',),' earth'),((' earthe.',),' earth.'),
            (('Eastwarde',),'Eastward'),(('eastwarde',),'eastward'), ((' easyer',),' easier'), ((' eest ',),' east '),((' eest,',),' east,'),((' eest.',),' east.'),
            ((' eeten',' eten'),' eaten'),((' eateth',' etith'),' eateth/eats'),((' eatinge',' etynge',' eatyng',' etyng'),' eating'),
                (('Eate ','Ete '),'Eat '),((' eate ',' eete ',' ete ',' eet '),' eat '),((' eate,',' ete,',' eet,'),' eat,'),((' eate.',' ete.',' eet.'),' eat.'),((' eate?',),' eat?'),((' eate:',' ete:'),' eat:'),((' eate;',' ete;'),' eat;'),
        ((' effecte',),' effect'),
        ((' egge',),' edge'),
            (('edificacioun',),'edification'), (('edyfyinge','edifyenge'),'edifying'), (('Idumee','Idume'),'Edom'),
        (('Egypte','Egipte','Egipt'),'Egypt'), (('Egipcians',),'Egyptians'),
        ((' eiyetithe',' eiytethe',' eiytthe'),' eighth'), (('eighteene','eightene','eiytene'),'eighteen'), (('eiytetithe',),'eightieth'), ((' eiyti',),' eighty'), ((' eiyte',' eyght'),' eight'),
            (('Ethir ',),'Either '),((' eithir ', ' ethir ',' ether '),' either '),
        (('Effraym','Efraym'),'Ephraim'),
        (('Elde ',),'Elder '),((' eldere',' eldre',' eldri'),' elder'),
            ((' electes',' elects'),' elect’s'),((' electe ',),' elect '),((' electe.',),' elect.'),
                ((' elemente',),' element'),
                ((' enleuenthe',' eleuenthe',' eleuenth',' eleueth',' leuenth'),' eleventh'),((' eleuen',),' eleven'),((' eleve ',),' eleven '),
            ((' elmes',),' elms'),((' elme,',),' elm,'),
            ((' ellis ',' els '),' else '),((' els,',),' else,'),((' els.',),' else.'),
        ((' embraceth',' enbraceth'),' embraceth/embraces'),((' imbrace ',),' embrace '),
            (('Emeralde','Emerauld','Emeraud',),'Emerald'),((' emeralde',' emeraude',' emeraud',),' emerald'),
            ((' enimitie',' enmitie'),' enmity'),
            (('Emperours',),'Emperors'),((' emperouris',' emperours'),' emperors'),(('Emperoure',),'Emperor'),((' emperoure',' emperour'),' emperor'),
                ((' imploy',),' employ'),
                ((' emptie ',),' empty '),((' emptie,',),' empty,'),((' emptie.',' emptye.'),' empty.'),
        ((' encampeth',' incampeth'),' encampeth/encamps'),((' encampe ',),' encamp '),
                (('enchauntmentes','inchantments'),'enchantments'), ((' enchaunteri',' inchanter'),' enchanter'),
                ((' inclose',),' enclose'),
                ((' incourage',),' encourage'),
            ((' endid',),' ended'),((' endyng',),' ending'), ((' endes',' endis'),' ends'),((' eende ',' ende '),' end '),((' ende,',),' end,'),((' ende.',),' end.'),((' ende?',),' end?'),((' ende:',),' end:'),((' ende;',),' end;'),
                ((' indaunger',' indanger'),' endanger'),
                ((' endeuoured',),' endeavoured'),((' endeuours',),' endeavours'),((' endeuoure ',' endeuour ',' indeuour '),' endeavour '),
                ((' endlesse',),' endless'),((' endles,',),' endless,'),
                ((' indure',),' endure'),
            ((' enemyes',),' enemies'),((' enemye ',' enemie ',' enimie '),' enemy '),((' enemie,',' enemye,'),' enemy,'),((' enemie.',' enemye.'),' enemy.'),((' enemie:',),' enemy:'),((' enemie?',' enemye?'),' enemy?'),
            ((' engyne',),' engine'), ((' engraue',),' engrave'),
            (('enhaunside','enhaunsid'),'enhanced'),((' enhanceth',' enhaunsith'),' enhanceth/enhances'),(('enhaunsinge','enhaunsyng'),'enhancing'), ((' enhaunse ',' enhaunce '),' enhance '),
            ((' enjoyeth',' enioyeth'),' enjoyeth/enjoys'),((' enioye ',' enioy '),' enjoy '),
            ((' inlarge',' alarge'),' enlarge'), ((' inlightn',),' enlighten'),
            (('ynough','inough'),'enough'),
            ((' inquir',),' enquir'),
            ((' inrich',),' enrich'),
            ((' ensigns',' ensignes'),' ensigns/flags'),((' ensign ',' ensigne '),' ensign/flag '),
            ((' entysed',' entised'),' enticed'),((' entise ',),' entice '),
                ((' entred',' entriden',' entride',' entrid',' intred'),' entered'),((' enterest',' entrist'),' enterest/enter'),((' entereth',' entreth',' entrith'),' entereth/enters'),((' entringe',' entrynge',' entryng',' entring',' entren'),' entering'), (('Entre ',),'Enter '),((' entre ',),' enter '),((' entre,',),' enter,'),
                ((' entrailis',),' entrails'), ((' intraunce',),' entrance'), ((' intreated',),' entreated'),((' entreate ',' intreate ',' intreat '),' entreat '),
                ((' entryes',),' entries'),((' entrie ',),' entry '),((' entrie.',),' entry.'),
            ((' enuious',),' envious'), ((' enuied',),' envied'),((' enuiyng',),' envying'),  ((' enuie ',' enuye ',' enuy '),' envy '),((' enuie,',' enuye,'),' envy,'),
        ((' epistlis',),' epistles/letters'),
        ((' vnequall ',),' unequal '),((' vnequall.',),' unequal.'),((' vnequall?',),' unequal?'), ((' equall ',),' equal '),((' equall,',),' equal,'),((' equall.',),' equal.'),((' equall?',),' equal?'),((' equall:',),' equal:'),
            ((' equitie',' equytee',' equite',' equyte'),' equity'),
        ((' ere ',' yer '),' ere/before '),
            ((' erryden',),' erred'),((' erreth',' errith'),' erreth/errs'),
                ((' erronious',),' erroneous'),
                ((' erren ',' erre '),' err '),((' erre,',),' err,'),((' erre.',),' err.'),((' erre?',),' err?'),((' erre;',),' err;'), ((' erroure',' errour'),' error'),
        ((' ascapidist',),' escaped'),((' escapeth',' ascapith'),' escapeth/escapes'),((' ascape',),' escape'),
            ((' eschuynge',),' eschewing/avoiding'),
            ((' establishe ',),' establish '),
                ((' esteeme ',),' esteem '),
        ((' eternall ',),' eternal '),
        (('Eunuches',),'Eunuchs'),((' eunuches',),' eunuchs'),
        (('euangelisynge',),'evangelising'),
            ((' eue ',),' eve/even '),(('Euen',),'Even'),((' euene ',' euen ',' evyn '),' even '),((' euen,',),' even,'),(('(euen ',),'(even '),
                ((' euenynge',' eueninge',' euenyng',' euening'),' evening'), ((' euenli',),' evenly'),
                ((' euentid ',),' eventide/evening '), ((' euent',),' event'),
            (('euerlastyngnesse',),'everlastingness'),(('everlastinge','euerlastynge','euerlastyng','euerlastinge','euerlasting'),'everlasting'), ((' eueremore',' euermore'),' evermore'),
                (('euerythinge','everythinge'),'everything'), (('Euery',),'Every'),((' euery',' euerie'),' every'),#(('>euery',),'>every'),
                (('Euere','Euer'),'Ever'),((' euere',' euer'),' ever'), #((' euere ',' euer '),' ever '),
        ((' euidence',),' evidence'),((' euident',),' evident'),
            (('Euilmerodach','Euil-merodach','Euylmeradach'),'Evil-merodach'), ((' yuelis',),' evils'),((' evyll',' euell',' euill',' euil',' euyll',' euyl',' evell',' evill',' yuele',' yuel',' euel'),' evil'),
        ((' yowes',),' ewes'),
        ((' exalte ',),' exalt '),
                (('Examen',),'Examine'),((' examen',),' examine'),
            ((' exceaded',),' exceeded'), (('excedyngly','exceadingly','exceedyngly','exceadyngly','excedingly'),'exceedingly'),((' exceadinge',),' exceeding'),((' exceede ',' exceade '),' exceed '),((' exceede,',),' exceed,'),
                ((' excel ',),' excell '), (('excellentnesse',),'excellentness/excellence'), ((' excellencie ',),' excellency '), ((' excelletn ',' excellet '),' excellent '),
                (('Excepte ',),'Except '), ((' excepte ',),' except '),
                ((' excitid ',' exitid '),' excited '),
                ((' excludid',),' excluded'),
            (('execucion',),'execution'), ((' exercisid',),' exercised'),((' exercyse ',),' exercise '),
            (('expectingly',),'expectantly'),
                    ((' expences',),' expenses'),
                    ((' experiece',),' experience'), ((' experte ',),' expert '),
                    ((' expownede',),' expounded'),((' expownyng',),' expounding'),((' expowne ',),' expound '),
                ((' expresly',),' expressly'), ((' expressid',),' expressed'), ((' expresse ',),' express '),((' expresse.',),' express.'),
            ((' extincte',),' extinct'),
                ((' extoll ',' extold '),' extol '), (('extorcion',),'extortion'),
                (('extremitie,',),'extremity,'),
        ((' iyen ',),' eyes '),((' iyen,',),' eyes,'),((' iyen.',),' eyes.'),((' iyen;',),' eyes;'),((' eies',),' eyes'),((' eie ',' iye '),' eye '),((' iye,',' ey,'),' eye,'), # ((' eies:',),' eyes:'),
    ((' fablis',),' fables'),
        ((' facis',),' faces'),
        ((' vading',),' fading'), # Psa 109:23
        ((' failiden',' failide',' failid',' fayled'),' failed'),((' failest',' faylest'),' failest/fail'),((' faileth',' fayleth',' faeleth',' failith',' faylith'),' faileth/fails'),((' failinge',),' failing'), ((' fayle ',' faile '),' fail '),((' failen,',' fayll,',' faile,',' fayle,'),' fail,'),((' faile.',' fayle.'),' fail.'),((' faile:',),' fail:'),((' faile;',),' fail;'),
                ((' faynted',),' fainted'),((' fainteth',' faynteth'),' fainteth/faints'),((' faynte ',' faynt '),' faint '),((' faynt,',),' faint,'),((' faynt.',),' faint.'),
                ((' fairenesse',' fairnesse'),' fairness'),((' fairere ',' feirere ',' fayrer '),' fairer '),((' faireste',' fayrest'),' fairest'), ((' faire ',' fayre '),' fair '),((' faire,',' fayre,'),' fair,'),((' faire:',),' fair:'),((' faire;',),' fair;'),
                ((' faithlesse',' faythlesse'),' faithless'), ((' feith',' fayth'),' faith'),
                    ((' faithfull ',),' faithful '),((' faithfull,',),' faithful,'),((' faithfull.',),' faithful.'),((' faithfull:',),' faithful:'), (('faithfulnesse',),'faithfulness'),(('faythfulnes ','faithfulnes '),'faithfulness '),(('faithfulnes,',),'faithfulness,'),(('faithfulnes.',),'faithfulness.'),
            ((' fallun',),' fallen'),((' falle:',),' fallen:'),((' fallinge',' fallynge',' fallyng'),' falling'), ((' falles',),' falls'), (('Falle ',),'Fall '),((' faule ',' falle ',' fal '),' fall '),((' falle,',' fal,'),' fall,'),
                    ((' fallow ',' fallowe '),' fallow/ploughed '),
                (('falshoode','falshood'),'falsehood'),((' falsnesse',),' falseness'),
                    ((' falslye',' falsly'),' falsely'), ((' falsifie ',),' falsify '), (('Fals ',),'False '),((' falce ',' fals '),' false '),
            ((' familiarite',),' familiarity'), ((' familier ',),' familiar '),
                    ((' familie ',),' family '),((' familie,',),' family,'),
                    ((' famin,',),' famine,'),
                    ((' famishinge',),' famishing'),((' famyshment',),' famishment'),
                ((' famouse',),' famous'),
            ((' fanne ',),' fan '),((' fanne,',),' fan,'),((' fanne.',),' fan.'),
            ((' farthynge',' farthinge',' farthyng',' ferthing'),' farthing'),
                    (('Farre ',),'Far '),((' farre ',' fer '),' far '),((' farre,',' fer,'),' far,'),((' farre.',' fer.'),' far.'),((' farre?',' fer?'),' far?'),((' fer;',),' far;'),
                ((' farewel ',),' farewell '),
             (('fashioneth','facioneth'),'fashioneth/fashions'),((' facion',),' fashion'),
                ((' faste ',),' fast '),((' faste,',),' fast,'),((' fastiden',),' fasted'),((' fastynge',' fastyng',' fastinge'),' fasting'), (('fastnyde','fastned'),'fastened'),
            ((' fatnesse',),' fatness'),((' fatnes.',),' fatness.'),((' fatnes:',),' fatness:'), ((' fatte ',' fatt '),' fat '),((' fatte,',),' fat,'),
                (('fatherlesse','fadirles','faderles'),'fatherless'), (('Fadris',),'Fathers'),((' fadrys',' fadris',),' fathers'), (('Fadir',),'Father'),((' fadir',),' father'),
            ((' faultes',' fautes'),' faults'), ((' faultie',),' faulty'), ((' faute ',' fawte '),' fault '),((' faute:',),' fault:'),
            ((' fauorable',),' favourable'),
                ((' favourest',' fauouredst',' fauourest'),' favourest/favour'),((' favoureth',' fauoureth'),' favoureth/favours'),((' fauoured',),' favoured'),((' fauoure',' fauour',' favor',' fauor'),' favour'),
            ((' faun',),' fawn'),
        ((' feares',),' fears'), (('Feare ',),'Fear '),(('Feare,',),'Fear,'),((' feare ',),' fear '),((' feare,',),' fear,'),((' feare.',),' fear.'),((' feare?',),' fear?'),((' feare:',),' fear:'),
                    (('Fearfullnesse ','Fearefulnesse ','Fearefulnes '),'Fearfulness '),(('fearefull ','fearfull ','ferdful '),'fearful '),(('fearefull,','feareful,','feerful,'),'fearful,'),(('fearfull.',),'fearful.'),(('fearefull?','fearfull?'),'fearful?'),(('fearefull:','fearfull:'),'fearful:'),
                (('feastes',),'feasts'),((' feeste ',' feaste ',' feest '),' feast '),((' feeste,',),' feast,'),((' feeste.',),' feast.'),
                (('fetherid',),'feathered'),((' fetheris',),' feathers'),((' fether',),' feather'),
            ((' fedden ',' fedde '),' fed '),((' fedde:',),' fed:'),
            ((' feble',),' feeble'),#((' feble,',),' feeble,'),((' feble;',),' feeble;'),
                ((' feedeth',' fedeth'),' feedeth/feeds'),((' fedynge',' fedinge'),' feeding'), (('Feede ','Fede '),'Feed '),((' feede ',' fede '),' feed '),((' feede,',' fede,'),' feed,'),((' feede.',),' feed.'),
                ((' feele ',),' feel '),
                ((' feete',' fete'),' feet'),
            ((' vnfained',),' unfeigned'),((' fained',),' feigned'),((' faine ',),' feign '),
            ((' fellest',' fellist'),' fellest/fell'),((' felden ',' fellen ',' felle ',' fel '),' fell '),
                (('fellishepe','felouschipe'),'fellowship'),((' felowis',' fellowes'),' fellows'),((' felowe',' felow'),' fellow'),
                ((' felte',' felide'),' felt'),
            ((' femal ',),' female '),((' femal,',),' female,'),
            ((' fery',),' ferry'),
                ((' feruentli',),' fervently'),((' feruent',),' fervent'), ((' feruour',),' fervour'),
            ((' fitchid ',' fetcht ',' fet '),' fetched '),((' fetche ',),' fetch '),
            ((' feuer',),' fever'),
            ((' feawe ',' fewe '),' few '),((' fewe,',),' few,'),((' feawe.',' fewe.'),' few.'),((' fewe:',),' few:'),((' fewe;',),' few;'),
        ((' fidelitie ',),' fidelity '),
                ((' feeldis',' fieldes',' feldes'),' fields'),((' fielde ',' feeld ',' felde ',' feld '),' field '),((' fielde,',' felde,',' feeld,',' fiede,'),' field,'),((' fielde.',' feeld.',' felde.'),' field.'),((' fielde:',' felde:'),' field:'),((' feeld;',),' field;'),
                ((' fiends',' feendis',' fendis'),' fiends/devils'),((' fiend ',' fiende ',' feend ',' fende '),' fiend/devil '),((' fiend,',' fiende,',' feend,'),' fiend/devil,'),
                (('fiercenesse ','fersnesse ','fiercenes '),'fierceness '), ((' fierie ',' firie ',' fyry ',' firy '),' fiery '),
            ((' fiftenthe',),' fifteenth'),((' fifteene ',' fiftene '),' fifteen '), ((' fiftithe',),' fiftieth'), ((' fyuethe ',' fyfth ',' fyft ',' fift '),' fifth '),((' fyuethe,',' fift,',' fyft,'),' fifth,'), ((' fyfties',),' fifties'),
                ((' fyftye ',' fiftye ',' fiftie ',' fifti '),' fifty '),((' fyftye,',' fiftie,'),' fifty,'),((' fyftye.',' fiftie.',' fyftie.'),' fifty.'),((' fiftie:',' fiftye:'),' fifty:'),((' fifti;',),' fifty;'),
            ((' figges',' fygges',' fyges',' figis'),' figs'),((' fygge ',' fyge ',' figge ',' fige ',),' fig '),
                ((' fiyteris',),' fighters'),((' fiytere',),' fighter'), ((' fighteth',' fiytith'),' fighteth/fights'),((' fightinge',' fiytyng',' fyghtyng',' fiyten'),' fighting'),(('Fyght',),'Fight'),((' fighte ',' fiyte '),' fight '),((' fighte.',),' fight.'),((' fyght',),' fight'),
                ((' figuratif',),' figurative'),((' fygure ',),' figure '),
            ((' fillest',' fyllest'),' fillest/fill'),((' filleth',' fylleth',' fillith'),' filleth/fills'),((' filliden',' fillide',' fillid',' fylled'),' filled'),#((' fillid,',),' filled,'),((' fillid.',),' filled.'),((' fillid:',' fylled:'),' filled:'),
                    ((' fillid;',),' filled;'),((' fyll ',' fille ',' fyl '),' fill '),
                (('fylthynesse','filthinesse','filthynesse','fylthinesse','filthynes','fylthines'),'filthiness'),((' filthines ',),' filthiness '), ((' filthie ',' fylthie ',' fylthy '),' filthy '), ((' filthis',),' filths'), ((' filthe',),' filth'),
            ((' finnes',),' fins'),
            ((' fyndyngis',),' findings'),((' fyndynge',),' finding'), ((' findeth',' fyndeth',' fyndith',' findith'),' findeth/finds'), ((' fynde ',' finde '),' find '),((' fynde.',),' find.'),
                ((' fyne',),' fine'),
                ((' fyngers',' fyngris'),' fingers'),((' fynger ',' fyngur '),' finger '),
                ((' fynished',),' finished'), ((' fynnyssher',' fynissher',' finissher'),' finisher'),
            (('Firre ','Fyrre '),'Fir '),((' firre ',' fyrre '),' fir '),((' firre.',),' fir.'),
                ((' firis',),' fires'), (('Fier','Fyre'),'Fire'),((' fier ',' fyre '),' fire '),((' fier,',' fyre,',' fyer,'),' fire,'),((' fier.',' fyre.'),' fire.'),((' fier?',' fyre?'),' fire?'),((' fyre:',),' fire:'),((' fier;',),' fire;'),
                ((' firme ',),' firm '), (('firmamet',),'firmament'),
                ((' fyrste',' firste',' fyrst'),' first'),
            (('fischis','fisshes','fysshes','fyshes'),'fishes'),(('fisscheris','fisshers','fysshers','fyshers','fy?shers'),'fishers'), ((' fishe ',),' fish '),((' fisch',' fysh'),' fish'),
                ((' fistes',),' fists'),
            ((' fyt ',),' fit '),
            (('Fiue','Fyue'),'Five'),((' fyue',' fyve',' fiue'),' five'),
        ((' flamyng',),' flaming'), ((' flambes ',' flammes '),' flames '),((' flawme',' flambe',' flamme'),' flame'),
                ((' flankes',),' flanks'),
                ((' flaxe ',),' flax '),((' flaxe,',),' flax,'),
            ((' fleddest',' fleddist'),' fleddest/fled'),((' fledden',' fledde'),' fled'), ((' fleynge',),' fleeing'), (('Fle ',),'Flee '),((' flye ',' fleen ',' fleiy ',' fle '),' flee '),((' flye,',' fle,'),' flee,'),((' fle.',),' flee.'),((' fle)',),' flee)'),
                    ((' fleeteth',' fletith'),' fleeteth/fleets'),((' fletynge',),' fleeting'),
                (('Fleischli ',),'Fleshly '),((' fleischli ',),' fleshly '),((' fleischis',' flesshe',' fleshe',' fleische',' fleisch',' flesch',' flessh'),' flesh'),
            (('Fliyt ','Flyt '),'Flight '),((' flyght ',),' flight '),
                ((' flynt',),' flint'),
            ((' flote',),' float'),
                (('flockis','flockes'),'flocks'),(('flocke ','floc ','flok '),'flock '),(('flocke,','floc,'),'flock,'),(('flocke.','floc.'),'flock.'),(('flocke:',),'flock:'),(('floc;',),'flock;'),
                (('fluddes','floudes','flouds','floodes','floodis','flodis'),'floods'),((' floude ',' fludde ',' flud '),' flood '),(('floude,',),'flood,'), ((' floore',),' floor'),#(('floore,',),'floor,'),(('floore.',),'floor.'),
                (('florischynge','florishinge','florishyng'),'flourishing'), (('florische ','florishe '),'flourish '),(('florishe,',),'flourish,'),(('florishe:',),'flourish:'),(('floorish','florish'),'flourish'),
                (('flowre ','floure '),'flour '),((' flowre,',' floure,'),' flour,'),((' flowre:',' floure:'),' flour:'),((' flowre;',),' flour;'),
                (('flouride','flourid'),'flowered'), (('Flouris ',),'Flowers '),((' flowres ',' floures ',' flouris '),' flowers '),((' floures.',),' flowers.'),
                    (('flowen ',),'flown '),((' flowiden',),' flowed'),(('flowith ','floweth '),'floweth/flows '),((' flowe ',),' flow '),((' flowe,',),' flow,'),((' flowe.',),' flow.'),
                ((' fluxe ',),' flux '),
                ((' flieth',' flyeth'),' flieth/flies'),((' flyenge',' fliynge'),' flying'),((' flyes',),' flies'),((' flie ',' fley '),' fly '),((' flie,',),' fly,'),((' flie.',),' fly.'),((' flie:',),' fly:'),
        ((' foale',),' foal'),
                    ((' foameth',' fometh'),' foameth/foams'),((' fomede',' fomed'),' foamed'),((' fomynge',' foming',' fomyng'),' foaming'),((' fome ',),' foam '),
            ((' foder',),' fodder/food'),
            ((' foldid',),' folded'),((' foldeth',' foldith'),' foldeth/folds'),
                    ((' folds',' foldes',' foldis'),' folds/pens'),((' foold ',),' fold '),((' foold,',' folde,'),' fold,'),
                (('Folks','Folkis',),'Folks/People'),((' folks',' folkis',' folkes'),' folks/people'), ((' folk ',' foolke ',' folke ',' folc '),' folk/people '),((' folk,',' folke,',' folc,',),' folk/people,'),((' folk.',' folke.',' folc.'),' folk/people.'),((' folk:',' folke:',),' folk/people:'),
                ((' followeth',' foloweth'),' followeth/follows'),((' folowed',' foleweden',' folewiden',' sueden',' suede'),' followed'),(('folowynge','folewynge','folowinge','folowyng','folowing'),'following'), (('Folowe','Folow'),'Follow'),((' followe ',' folowe ',' folow ',' suen '),' follow '),((' folowe:',),' follow:'),
                    ((' foli ',),' folly '),((' follie,',' foli,'),' folly,'),((' follie.',' fooli.',' foli.'),' folly.'),((' follie:',),' folly:'),((' follie;',' foli;'),' folly;'),
            ((' foode ',),' food '),((' foode,',' fode,'),' food,'),((' foode:',),' food:'),
                ((' foolis ',' fooles '),' fools '),((' foolis,',' fooles,'),' fools,'),((' foolis.',' fooles.'),' fools.'),((' fooles:',),' fools:'),((' fooles;',),' fools;'), # Needs a trailing space coz of foolish
                        ((' foole ',),' fool '),((' foole,',),' fool,'),((' foole.',),' fool.'),((' foole?',),' fool?'),((' foole:',),' fool:'),
                    (('foolishnesse','folishnesse','foolyshnes','folysshnes'),'foolishness'),(('foolishnes ','folishnes '),'foolishness '),(('foolishnes.','folishnes.'),'foolishness.'),(('foolishnes?',),'foolishness?'),(('foolishnes:',),'foolishness:'), ((' foolishe',' folish',' fonned'),' foolish'),
                ((' footemen',),' footmen'), (('footesteppes','footsteppes','footesteps','fotestoppes','fotesteppes','foote-steppes'),'footsteps'), ((' foote ',' fote '),' foot '),((' foote,',' fote,'),' foot,'),((' foote.',' fote.'),' foot.'),((' foote:',),' foot:'),
            ((' forbad ',),' forbade '),((' forbeare',),' forbear'), ((' forbydden',' forbodun'),' forbidden'), (('Forbede ','Forbyd '),'Forbid '),((' forbeed ',' forbede ',' forbyd '),' forbid '),
                ((' foordes',' fordes'),' fords'),
                ((' forecourte',),' forecourt'),
                ((' foreheade',' forheed'),' forehead'), ((' forreiners ',),' foreigners '),((' forraine ',),' foreign '), ((' foresti',' foreste',' forrest'),' forest'),
                ((' forgavest',' forgauest'),' forgavest/forgave'),((' forgaue',),' forgave'),
                    ((' foryetyng',' foryeting'),' forgetting'), (('Foryete',),'Forget'),((' foryete',),' forget'),
                    (('forgiuenesse',),'forgiveness'),(('forgeuenes,',),'forgiveness,'),(('forgevenes:',),'forgiveness:'),
                        (('forgeven','foryouun','forgeuen','forgiuen','foryyuen','foryoue'),'forgiven'), ((' forgivest',' foryyuest'),' forgivest/forgive'),((' forgiveth',' forgiueth',' forgeueth'),' forgiveth/forgives'), ((' foryyuynge',),' forgiving'), ((' forgiue ',' foryyue ',' forgeve ',' forgeue '),' forgive '),((' foryyue,',' forgiue,',' forgeue,'),' forgive,'),((' forgiue.',),' forgive.'),((' forgiue:',' forgeue:',),' forgive:'),
                    ((' foryaten',),' forgotten'),((' forgotte.',),' forgotten.'), ((' forgate',' forgat',' foryat'),' forgot'),
                ((' formere ',),' former '), ((' fourmedist',' fourmed'),' formed'),((' formeth',' fourmeth'),' formeth/forms'), ((' formes',),' forms'), ((' fourme ',' forme '),' form '),((' fourme,',' forme,'),' form,'),((' forme:',),' form:'),
                (('Fornycacioun',),'Fornication'),(('fornicacioun','fornycacioun','fornicacion',),'fornication'),
                ((' forsakun',),' forsaken'),((' forsaketh',' forsakith'),' forsaketh/forsakes'),((' forsakynge',),' forsaking'),((' forsooke',' forsoken',' forsoke',),' forsook'),
                    ((' foreskinne',),' foreskin'),
                    ((' fourthe',' foorth',' forthe'),' forth'),
                ((' fortifie ',),' fortify '),
                    ((' fortresse ',),' fortress '),((' fortresse,',),' fortress,'),((' fortresse.',),' fortress.'),((' fortresse:',),' fortress:'),
                    ((' fortes',),' forts'), ((' fourtithe',' fourtieth',' fourtith',' fortyth'),' fortieth'), (('Fourtie ','Fortie '),'Forty '),((' fourtie ',' fourtye ',' fortye ',' fouretie ',' fourty ',' fourti ',' fortie '),' forty '),((' fourti,',),' forty,'),
                    ((' forwarde',),' forward'),
            ((' fauyte ',' foughte ',' fouyten ',' fouyt ',' fauyt '),' fought '),
                ((' foundide',' foundid'),' founded'),((' foundun ',' founden ',' fonden ',' foonde ',' founde ',' foude ',' fande ',' foond ',' foud '),' found '),((' founde,',),' found,'),((' foundun.',' founde.'),' found.'),((' founde:',),' found:'), (('foundacions','foundacios'),'foundations'),((' foundacion ',' foundatio ',' foundacio '),' foundation '),
                    ((' fountaine',' fountayne',' foutayne'),' fountain'),
                ((' fouretenthe',' fourtenthe',' fourtenth'),' fourteenth'),((' foureteene',' fourteene',' fourtene'),' fourteen'),((' fowre',' foure',' fower'),' four'),
            ((' fouler',),' fowler'),((' fowls',' fowles',' foules',),' fowls/birds'),((' fowl ',' foule ',),' fowl/bird '),((' foule,',),' fowl/bird,'),((' foule.',),' fowl/bird.'),((' fowl:',' foule:'),' fowl/bird:'),((' fowl;',),' fowl/bird;'), # ((' foules,',),' fowls/birds,'),((' foules.',),' fowls/birds.'),((' foules:',),' fowls/birds:'),
            ((' foxis',),' foxes'),((' foxe ',),' fox '),
        ((' fragmentes',),' fragments'), ((' fraile ',),' frail '),
                (('frankencense','frankensence','frankynsense'),'frankincense'),
                ((' franticke ',),' frantic '),
                ((' fraude',),' fraud'),
            (('Fre ',),'Free '),(('Fre.',),'Free.'),((' fre ',),' free '),((' fre.',),' free.'),
                ((' freedome',' fredom'),' freedom'), ((' freli',' frely'),' freely'), ((' freewyll',' frewill',),' freewill'),((' freewil ',),' freewill '),
                (('frendshipe',),'friendship'), (('Frendis',),'Friends'),(('frendesse','frendis','frendes'),'friends'),((' friende',' freend',' frende',' frend'),' friend'),
                ((' freshe ',),' fresh '),((' freshe,',),' fresh,'),
                (('Frett ',),'Fret '),
            (('frogges',),'frogs'),
            (('Fro ',),'From '),((' fro ',' frō '),' from '), ((' frount',),' front'), (('frowarde ','froward ',),'froward/ornery_or_disobedient '),
            (('fruitfull ','frutefull ','fruytful ','fruteful '),'fruitful '),(('fruitfull,','frutefull,'),'fruitful,'),(('fruitfull.','fruitefull.','frutefull.','frutfull.'),'fruitful.'),(('fruitefull:',),'fruitful:'),
                (('fruites','fruitis','fruytis','frutes'),'fruits'),((' fruyt ',' frute ',' fruite ',' frut '),' fruit '),((' fruite,',' frute,',' fruyt,'),' fruit,'),((' fruite.',' frute.',' fruyt.'),' fruit.'),((' fruite:',' frute:'),' fruit:'),((' fruite;',),' fruit;'),
            (('friynge ','friyng '),'frying '),
        ((' fewell',),' fuel'),
            ((' fugitiues',),' fugitives'),
            ((' fulleste',),' fullest'),((' fulli',),' fully'), ((' fulle ',' ful '),' full '),((' ful,',),' full,'),((' ful.',),' full.'),((' ful;',),' full;'), (('fulfillid','fulfylled'),'fulfilled'),(('fulfillynge','fulfyllyng'),'fulfilling'), ((' fulfill ',' fulfull ',' fulfyll '),' fulfil '), ((' fulnesse ',' fulness ',' fulnes '),' fullness '),((' fulnesse,',' fulness,'),' fullness,'),((' fulnesse.',' fulness.'),' fullness.'),
            ((' furiousnes ',),' furiousness '),
                ((' fornace',' furneis'),' furnace'),
                ((' furrowes',' forrowes',' forowes',' forewis'),' furrows'),
                (('furtherance','furtheraunce'),'furtherance/advantage'), ((' ferthere',' ferther'),' further'),
                ((' furie ',),' fury '),((' furie,',),' fury,'),((' furie.',),' fury.'),
    ((' gaine ',),' gain '),((' gaine,',),' gain,'),((' gaine.',),' gain.'), (('Gayus',),'Gaius'),
            ((' galaries',),' galleries'), ((' galoun',),' gallon'), ((' gall ',' galle ',' gal '),' gall/bile '),((' gall,',' galle,'),' gall/bile,'),((' gall.',' galle.',),' gall/bile.'),
            ((' garmentes',' garmetes'),' garments'),((' garmente',' garmet'),' garment'),
                (('garnisshed','garnysshed'),'garnished'),
                (('garison',),'garrison'),
            ((' gappes',),' gaps'),
            ((' yatis',),' gates'),((' yate',),' gate'), (('gaderiden','gadirid','gaderide','gaderid','gaddered','gadered','gaddred'),'gathered'),((' gathereth',' gaderith'),' gathereth/gathers'),((' gatheringe',' gaderynge',' gadering'),' gathering'), (('Gadere ',),'Gather '),((' gadere ',' gaddre ',' gadre ',' geder '),' gather '),((' gadere.',),' gather.'),
            ((' gavest',' gauest',' yauest'),' gavest/gave'),((' yaf ',' gaue ',' yauen ',' yeuen ',' yaue '),' gave '),((' yaf,',' gaue,'),' gave,'),#(('>gaue ',),'>gave '),
            ((' gasinge',),' gazing'),((' gase ',),' gaze '),
        ((' geare ',' geer ',' gere '),' gear '),
            ((' generall ',),' general '),
                (('genologies',),'genealogies'),(('genealogie ',),'genealogy '),(('genealogie,',),'genealogy,'),(('genealogie.',),'genealogy.'), (('generacios',),'generations'), (('Generacioun',),'Generation'),(('generacioun','generacion','generacio'),'generation'),
                (('Gentyles','Getiles'),'Gentiles'),((' gentyls',),' gentiles'),
                    (('gentlenesse',),'gentleness'),(('gentlenes:',),'gentleness:'), ((' getly',),' gently'),
            (('Gett ',),'Get '),((' gett ',),' get '),
        ((' goost',' ghoste'),' ghost'),
        (('Gyant','Giante'),'Giant'),((' giaunti',' giaunte',' giaunt',' giaute',' gyant'),' giant'),
            (('giddines.',),'giddiness.'),
            ((' giftes',' gyftes',' yiftis'),' gifts'),((' gifte ',' yifte '),' gift '),((' yifte;',),' gift;'),((' gyft',),' gift'),
            ((' ginne ',),' gin '),
            ((' gyrded',),' girded'),((' girdeth',' gyrdeth'),' girdeth/girds'), ((' girdil',' gerdyll',' gyrdle',' gerdell'),' girdle'), (('Girde ','Gyrde '),'Gird '),((' girde ',' gyrde '),' gird '),
                ((' girles',),' girls'),((' girle ',' gyrle '),' girl '),
            ((' yyueris',),' givers'),((' giuer',' yyuer'),' giver'),
                ((' givest',' giuest',' geuest',' yyuest'),' givest/give'),((' giveth',' giueth',' yyueth',' yiueth',' geueth'),' giveth/gives'), ((' geven',' giuen',' geuen',' youun',' youe',' yyuen'),' given'),((' geve.',),' given_to.'), ((' giuing ',' geuynge ',' geuyng ',' geuing '),' giving '),
                (('Geue ','Giue ','Yyue ','Yiue '),'Give '),((' geve ',' geue ',' giue ',' yyue ',' yiue '),' give '),((' geve,',' geue,',' giue,',' yyue,'),' give,'),((' giue?',' yyue?',' geue?',' geve?'),' give?'),
        (('gladiden',),'gladdened'),(('gladnesse',),'gladness'),(('gladnes ',),'gladness '),(('gladnes,',),'gladness,'),(('gladnes.',),'gladness.'),(('gladnes:',),'gladness:'), (('gladli',),'gladly'),((' gladde ',),' glad '),
                ((' glasse',),' glass'),
            ((' glainer',),' gleaner'), ((' gleenynge',' gleanyng'),' gleaning'),
            ((' glisteringe',),' glistering'),
            (('gloominesse',),'gloominess'),(('gloomynge ','glomie '),'gloomy '),
                (('glorifieden',),'glorified'),((' glorifie ',),' glorify '), ((' gloriouse ',' glorius '),' glorious '), (('Glorie ',),'Glory '),((' glorie',' glorye'),' glory'),#((' glorie,',),' glory,'),((' glorie.',),' glory.'),((' glorie;',),' glory;'),
        ((' gnasheth',' gnassheth'),' gnasheth/gnashes'),((' gnashed',' gnaistiden'),' gnashed/grated'),((' gnash ',' gnashe ',' gnaste '),' gnash/grate '), ((' gnawe ',),' gnaw '),
        ((' goates',' gotes'),' goats'),(('Goate',),'Goat'),((' goet ',' gote ',' geet '),' goat '),((' goate',),' goat'), # Take care with 'goeth'
            ((' goblets',' goblettes'),' goblets/cups'),
            ((' goddesse ',),' goddess '), (('godlynesse',),'godliness'), (('Goddis',),'God’s'),((' goddes',' goddis',),' gods'),
            (('Goo ','Goe '),'Go '),(('Goo,','Goe,'),'Go,'),(('Goe.',),'Go.'),((' goe ',' goo '),' go '),((' goe,',),' go,'),((' goe.',' goo.'),' go.'),((' goe?',),' go?'),((' goe:',),' go:'),((' goe;',),' go;'),
            ((' goest',' goist'),' goest/go'),((' goeth',' goith'),' goeth/goes'), ((' goinges',' goynges',' goyngis'),' goings'),((' goen ',' gon '),' going '),((' goinge',' goynge',' goyng'),' going'), #((' goinge,',),' going,'),((' goinge.',),' going.'),((' goinge:',),' going:'),
            ((' goldun',),' golden'),((' golde ',),' gold '),((' golde,',),' gold,'),((' golde.',),' gold.'),((' golde:',),' gold:'), (('gold-smithes','goldesmithes','goldsmythes'),'goldsmiths'),
            (('Gomorah','Gomorre'),'Gomorrah'),(('Gomorra:',),'Gomorrah:'),
            ((' goon ',),' gone '),((' goon,',),' gone,'),
            ((' goodnesse',),' goodness'),((' goodnes ',),' goodness '),((' goodnes,',),' goodness,'),((' goodnes.',),' goodness.'),((' goodnes:',),' goodness:'), ((' gooddes',' goodis',' goodes'),' goods'), ((' goode ',),' good '),((' goode,',),' good,'),
            ((' gorgious',),' gorgeous'),
            (('Gospell',),'Gospel'),((' gospelle',' gospell'),' gospel'),
            (('Gouernour',),'Governor'),((' gouernouri',' gouernoure',' gouernour',' gouernor'),' governor'),((' gouerne ',),' govern '),((' goue',),' gove'),
        ((' gratiouslye',),' graciously'), (('Gratious',),'Gracious'),((' gratious',),' gracious'),
                ((' graine',' grayne'),' grain'),
                ((' graudfather',),' grandfather'),
                ((' grapis',),' grapes'),
                ((' grasse ',),' grass '),((' grasse,',' gras,'),' grass,'),((' grasse.',),' grass.'),((' grasse:',),' grass:'),((' grasse;',),' grass;'),
                    ((' grassehopper',' grashopper',' greshopper'),' grasshopper'),
                ((' graunted',' grauntide'),' granted'), (('Graunte ','Graunt '),'Grant '),((' graunte ',' graunt ',' grante ',' graute ',' graut '),' grant '),
                (('graved','grauyde','graued'),'graved/carved'),(('graven','grauen','grauun'),'graven/carved'),((' graving',' grauing'),' graving/carving'),((' graue',),' grave'),#((' graue,',),' grave,'),((' graue.',),' grave.'),((' graue:',),' grave:'),
                    ((' grauell ',),' gravel '),
                ((' graye ',' graie '),' gray '),
            (('grettere','gretter'),'greater'),(('grettest',),'greatest'), (('greatlye','greetli','greetly','gretli'),'greatly'), (('greatnesse','greetnesse'),'greatness'),(('greatnes ',),'greatness '),(('greatnes.',),'greatness.'), (('Greate ',),'Great '),(('greate ','grete ','greet ','grett ','gret '),'great '),(('greate,','greet,'),'great,'),(('grett.','greate.','greet.'),'great.'),(('greate:',),'great:'),
                    (('greaves','greaues'),'greaves/shin_armour'),
                (('gredili',),'greedily'),(('greedie ','gredy '),'greedy '),
                (('Grekes','Grekis'),'Greeks'),(('Grecians','Gretians'),'Grecians/Greeks'),
                (('greene ','grene '),'green '),(('grene,',),'green,'),(('greene.',),'green.'),(('greene:',),'green:'),
                (('gretinge','gretten'),'greeting'),
                ((' grewe',),' grew'),
            ((' griefe',' grefe'),' grief'),
                    (('grieuance',),'grievance'),(('grieued','greeued'),'grieved'),(('greeueth ',),'grieveth/grieves '), (('greeuouslye',),'grievously'),(('greeuous','grieuous'),'grievous'),((' greeue',' grieue',' greiue',' greue'),' grieve'),
                ((' grymme ',),' grim '),
                ((' grinde',),' grind'),
            (('gronynge','gronyng','groning'),'groaning'),(('grone ',),'groan '),(('grone?',),'groan?'),
                ((' groundes',),' grounds'),(('groundeth',),'groundeth/grounds'), (('grounde ','groude '),'ground '),(('grounde,','groude,'),'ground,'),(('grounde.','groude.','groud.'),'ground.'),(('grounde:',),'ground:'),
                    (('grutchynge','grutchyng'),'groutching/grudging'),
                (('groaue','groue',),'grove'),
                (('growinge',),'growing'), (('growne','growen'),'grown'), ((' grouth',),' growth'), ((' growe ',),' grow '),((' growe,',),' grow,'),
        ((' guardeth',' gardeth'),' guardeth/guards'),((' garde ',),' guard '),
                ((' gardes',),' gardens'),((' gardyn',),' garden'), ((' garlande',),' garland'),
            ((' gessiden',' gesside'),' guessed'),((' guessest',' gessist'),' guessest/guess'), ((' gessinge',),' guessing'), (('Gessist',),'Guess'),
                ((' ghestes',),' guests'), ((' ghest',' geest',' gest'),' guest'),
            ((' guyde',' gyde'),' guide'),
                ((' gilefuli',),' guilefully'),((' gileful',),' guileful'), ((' guyle ',' gile ',' gyle '),' guile '),((' gile,',),' guile,'),((' gile.',' guyle.',' gyle.'),' guile.'),
                    (('guiltlesse','giltlesse'),'guiltless'), ((' guiltie',' giltye',' giltie',' gilty',' gilti'),' guilty'),
                ((' gumme ',),' gum '),
            ((' gusshed',),' gushed'),((' gusshe ',' gu?she ',' gushe '),' gush '),
                ((' guttis',),' guts'),
    (('habitaciouns','habitacios'),'habitations'),(('habitacioun','habitacion','habitacio'),'habitation'),
            ((' hadden ',' hadde '),' had '),((' hadde,',),' had,'),((' hadde;',),' had;'), ((' hadst ',' haddest ',' haddist '),' hadst/had '),
            (('Haile',),'Hail'),((' hayle ',' haile ',' hale '),' hail '),((' haile,',' hayle,'),' hail,'),((' haile:',),' hail:'),
                ((' heerie',' hayrie',' heery'),' hairy'), ((' haires',' heeris',' heeres',' hayres',' hairis',' heiris'),' hairs'),((' haire ',' hayre ',' heer '),' hair '),((' haire,',' heere,',' heer,'),' hair,'),((' haire.',' heere.'),' hair.'),((' haire:',),' hair:'),
            ((' halfe',' halue'),' half'), #((' halfe ',' halue '),' half '),((' halfe,',),' half,'),((' halfe.',),' half.'),((' halfe:',),' half:'),
                (('Halleluiah','Hallelujah','Alleluia'),'Halleluyah'),(('Halleluya.',),'Halleluyah.'),
                    ((' hallis',),' halls'),((' halle ',),' hall '),((' halle,',),' hall,'),((' halle;',),' hall;'),
                        (('hallowed','halowed','halewide','halewid'),'hallowed/consecrated'),((' hallowing',' halewynge',' halewyng'),' hallowing/consecration'),((' hallow ',' halowe ',' halewe '),' hallow/consecrate '),
                ((' haltyng',),' halting'), ((' halte,',),' assert False, "We want to stop here",'),
            ((' handes',' hondes',' hoondis',' hondys',' hondis',' hodes',' hades'),' hands'),((' hande ',' honde ',' hoond ',' hond ',' hode ',' hade '),' hand '),((' hande,',' honde,',' hoond,',' hond,',' hode,',' hade,'),' hand,'),((' hande.',' honde.',' hond.',' hode.',' hade.'),' hand.'),((' hande?',' honde?',' hade?'),' hand?'),((' honde:',' hande:',' hode:',' hade:'),' hand:'),((' hond;',),' hand;'),((' honde)',),' hand)'),
                    ((' handfull',' hondful'),' handful'),
                    ((' handel',' hadle'),' handle'),
                    ((' handmaydens',' handmaydis'),' handmaidens'),((' handmayden',),' handmaiden'), ((' handmaidis',),' handmaids'),((' handmayde ',' handmaide '),' handmaid '),((' handmayd,',),' handmaid,'),((' handmayde.',' handmayd.'),' handmaid.'),((' handemayde:',' handmayde:',' handmaide:'),' handmaid:'),((' handmayd',),' handmaid'),
                ((' hangid',' haged'),' hanged'),((' hangeth',' hangith'),' hangeth/hangs'), ((' hanginges',),' hangings/curtains'), ((' hangma ',),' hangman '),
                    ((' hange ',' hage '),' hang '),
            ((' hapened',),' happened'),((' happe ',),' happen '),
                ((' happili',' happly',' haply'),' happily'), (('Happie ',),'Happy '),((' happie ',),' happy '),
            ((' hardnesse ',' hardnes '),' hardness '),((' harde ',),' hard '),
                ((' harlotte',' harloti'),' harlot'),
                ((' harme ',),' harm '),((' harme,',),' harm,'),((' harme.',),' harm.'),((' harme)',),' harm)'),
                ((' harnesse ',),' harness '),((' harnesse,',),' harness,'),((' harnesse:',),' harness:'),
                (('Harpe',),'Harp'),((' harpe',' harpi'),' harp'),
                ((' harrowe',' harowe'),' harrow'),
                ((' hartes',),' harts'),((' harte ',),' hart '),
                ((' haruest',' heruest',' hervest'),' harvest'),
            ((' hastiden',),' hastened/hurried'),((' hastide',),' hasted/hurried'),((' haistely',' hastely',' hastyly'),' hastily'),((' haistie ',' hastie ',' hastye '),' hasty '), ((' haist ',' haaste ',' haast '),' haste '),((' haist,',),' haste,'),((' haist:',),' haste:'),
            ((' hatefull ',),' hateful '),((' hatefull.',),' hateful.'), ((' hatide',),' hated'),((' hateth',' hatith'),' hateth/hates'),((' hatest',' hatidist',' hatist'),' hatest/hate'),((' hatinge',),' hating'), ((' hatiden',' haten'),' hate'),
                ((' hath ',),' hath/has '),
                ((' hatrede',),' hatred'),
            ((' hautines ',),' haughtiness '),((' hautines,',),' haughtiness,'),((' hautiness',),' haughtiness'),((' hautie',),' haughty'),
            ((' hauen',),' haven'),
                (('Haue ',),'Have '),((' haue ',' han '),' have '),((' haue,',),' have,'),((' haue.',),' have.'),((' haue?',),' have?'),#(('>haue ',),'>have '),((' haue<',),' have<'),
                (('Hauing',),'Having'),((' havinge',' hauinge',' hauing',' hauynge',' havynge',' hauyng'),' having'),
            ((' haye ',),' hay '),((' heye.',),' hay.'),
        (('Hee ',),'He '),((' hee ',),' he '),((' hee,',),' he,'),((' hee.',),' he.'),((' hee?',),' he?'),((' hee;',),' he;'),((' hee)',),' he)'),(('(hee ',),'(he '),
            ((' hedling',' heedlinges'),' headlong'), ((' heades',' heddes',' heedis'),' heads'),((' heade ',),' head '),((' heade,',),' head,'),((' heade.',),' head.'),
                ((' helide',' heelide',' heelid'),' healed'),((' healeth',' hilith'),' healeth/heals'),((' hilynge',' hilyng'),' healing'),((' heale ',),' heal '),((' heale:',),' heal:'),
                    (('Helthe',),'Health'),((' heelthe',' healthe',' helthe'),' health'), #((' helthe.',),' health.'),
                ((' heapinge',),' heaping'),((' heapes',' heepis',' hepis'),' heaps'), ((' heape ',' heep '),' heap '),((' heape,',),' heap,'),((' heape.',),' heap.'),((' heape:',),' heap:'),
                ((' herde ',),' herd/heard '),((' herde,',),' herd/heard,'),((' herde.',),' herd/heard.'), # Special ambiguous case
                ((' heardest',' herdest',' herdist',' herdst'),' heardest/heard'),((' hearde ',' herden '),' heard '),((' hearde,',' herden,'),' heard,'),((' herden;',),' heard;'),
                        ((' hearest',' herist'),' hearest/hear'),((' heareth',' herith'),' heareth/hears'),((' herynge',' hearyng',' heryng',' hearinge',' heringe',' heriyngi',' heriyng',' hering',' heren'),' hearing'),(('Heare ',),'Hear '),(('Heare,',),'Hear,'),((' heare ',' heere ',),' hear '),((' heare,',),' hear,'),((' heare.',),' hear.'),((' heare?',),' hear?'),((' heare:',),' hear:'),
                        ((' hearkned',' herkened'),' hearkened'),((' hearkeneth',' hearkneth',' harkeneth'),' hearkeneth/hearkens'), (('Herken ',),'Hearken '),((' herkene ',' herken ',' herkne '),' hearken '), (('Herke ',),'Heark '),
                    ((' hertli',),' heartily'),((' hertis',' hertes',' heartes'),' hearts'),((' hearte ',' herte ',' hert '),' heart '),((' herte,',' harte,',' hert,'),' heart,'),((' herte.',' hert.'),' heart.'),((' hert?',),' heart?'),((' herte:',' hert:'),' heart:'),((' herte;',),' heart;'), ((' harth ',),' hearth '),
                ((' heate ',' heete ',' heet '),' heat '),((' heete,',),' heat,'),((' heate?',),' heat?'),((' heate:',),' heat:'),((' heate;',),' heat;'), (('Hethene','Heythen','Heithen','Heithe','Heythe'),'Heathen'),((' hethene',' hethen'),' heathen'),
                ((' heuenli',),' heavenly'), (('Heuenes',),'Heavens'),((' heauens',' heuenes',' heuenys'),' heavens'), (('Heauen','Heuene','Heven'),'Heaven'),((' heauen',' heuene',' heuen',' heven', ' heaue'),' heaven'),
                        ((' heaued',),' heaved'),
                    ((' heauily',' heauyly',' heuely',' heuyli'),' heavily'),(('heauinesse','heuynesse'),'heaviness'),((' heauines,',' heuynes,'),' heaviness,'),(('heauines:','heuynes:'),'heaviness:'), ((' heauy ',' heauie ',' hevy ',' heuy '),' heavy '),((' heauie.',' heauy.',' heuy.'),' heavy.'),((' heauie,',' heauy,',' heuye,',' heuy,'),' heavy,'),((' heuy?',),' heavy?'),((' heauie:',' hevy:'),' heavy:'),((' heauie)',),' heavy)'),
            (('Hebruesse',),'Hebrewess'), (('Ebrewes','Ebrews','Ebrues','Hebrues','Hebrewes'),'Hebrews'), (('Hebrewe ','Hebrue ','Ebrewe ','Ebrew ','Ebreu '),'Hebrew '),((' hebrue ',),' hebrew '),
            ((' hegge',' heggi'),' hedge'),
            ((' hede ',' heede '),' heed '),((' heede,',' hede,'),' heed,'),((' heede:',' hede:'),' heed:'),
                ((' heeles',' heles'),' heels'),((' heele ',' hele '),' heel '),((' hele,',),' heel,'),((' heele.',),' heel.'),
            ((' heysfer',' heyffer',' heyfer'),' heifer'),
                ((' hights',),' heights'),((' heiythe',' heiyte',' heyght',' heigth',' heyth'),' height'),((' eiris',),' heirs'), ((' heyre ',' heire ',' eir '),' heir '),((' heire,',' heyre,'),' heir,'),((' heire:',' heyre:'),' heir:'),((' eire;',),' heir;'),
            ((' heldeth',' heldith'),' heldeth/holds'), (('HOLDEN',),'HELD'),((' helde ',),' held '),((' holdun',' holden',' hilid'),' held'),
                    ((' helle ',),' hell '),((' hellis,',' helle,',),' hell,'),((' helle.',),' hell.'),((' helle;',),' hell;'),
                        ((' helplesse',),' helpless'), ((' helpere',' helperi'),' helper'), ((' helpiden',' holpen',),' helped'),((' helpeth',' helpith'),' helpeth/helps'),
                            (('Helpe',),'Help'),((' helpe ',),' help '),((' helpe,',),' help,'),((' helpe.',),' help.'),((' helpe:',),' help:'),((' helpe;',),' help;'),((' helpe?',),' help?'),
                    ((' hense ',),' hence '),((' hece,',),' hence,'),((' hennus;',),' hence;'),
                ((' hemlocke',),' hemlock'), ((' hemmes',),' hems'),((' hemme ',),' hem '),
            (('Hir ',),'Her '), ((' hir ',' hyr '),' her '),((' hir,',' hyr,'),' her,'),((' hir.',),' her.'),((' hir?',),' her?'),((' hyr:',),' her:'),((' hir;',),' her;'),
                ((' hearbe',' herbe',' yerbe',' eerbe',' erbe',' erbi'),' herb'),
                (('heardman','herdman'),'herdsman'), (('hirdmen','hyrdmen','heardmen','herdmen'),'herdsmen'), ((' heards',' herdis'),' herds'),((' heerde',' heerd',),' herd'),
                ((' herafter',),' hereafter'),
                ((' heretage',' eritage',' erytage'),' heritage'),
                (('Erodians',),'Herodians'),(('Herodes',),"Herod's"),(('Herode ','Eroude '),'Herod '),(('Herode,','Eroude,'),'Herod,'),(('Herode:',),'Herod:'),
        ((' hiliden ',' hidde '),' hid '),((' hyd',),' hid'),
                ((' hidest',' hidist'),' hidest/hide'),((' hideth',' hidith'),' hideth/hides'), (('Hyde ',),'Hide '),
            ((' hygher ',' hiyere ',' hyer ',' hier '),' higher '), (('Hyest',),'Highest'),((' hyghest',' hiyeste',' hyeste',' hiyest',' hyest',' hiest'),' highest'), ((' hyghly',' hyelie'),' highly'), ((' hiynessis',),' highnesses'),((' hiynesse',' hyynesse'),' highness'),
                (('Hye ','Hiy '),'High '),(('Hie,',),'High,'),((' hygh ',' hye ',' hie ',' hiye ',' hiy '),' high '),((' hygh,',' hye,',' hiy,',' hie,'),' high,'),((' hygh.',' hye.',' hiy.'),' high.'),((' hygh:',),' high:'),
            (('Hillis',),'Hills'),((' hillis',' hilles',' hylles',' hils'),' hills'),(('Hil ',),'Hill '),((' hille ',' hyll ',' hil '),' hill '),((' hille,',' hyll,',' hil,'),' hill,'),((' hyll.',' hil.'),' hill.'),((' hyll:',),' hill:'),((' hille;',' hil;'),' hill;'),
            ((' hym ',),' him '),((' hym,',),' him,'),((' hym.',),' him.'),((' hym;',),' him;'),((' hym:',' hi:'),' him:'),((' hym?',),' him?'),((' hym)',),' him)'),
            (('Hyn ',),'Hin '),((' hynder',),' hinder'), (('Hindes',),'Hinds/Does'),((' hinds',' hyndes',' hindes',),' hinds/does'),((' hinde,',),' hind/doe,'),
                ((' hindges',),' hinges'),
            ((' heppis',' hipis'),' hips'),((' hipe ',),' hip '),((' hipe,',),' hip,'),
            ((' hiriden',' hiryde',' hiryd',' hyred',' hirid'),' hired'), ((' hyreling',),' hireling'), ((' hyre ',),' hire '),((' hyre,',),' hire,'),
            (('Hise ',),'His '),((' hise ',' hys '),' his '),
                ((' hyssed',),' hissed'),((' hissiden',' hissinge',' hisshing'),' hissing'),((' hisse ',),' hiss '),((' hisse,',),' hiss,'),
            ((' hither',' hyther',' hidder',' hidir',' hidur'),' hither/here'), (('Hittittes','Hethites','Etheis'),'Hittites'),
            (('Heuites','Hiuites','Heuytes','Eueys','Euey'),'Hivites'),
        ((' hoar ',' hoare ',' hoore '),' hoar/grey '),
            ((' holdeth',' holdith'),' holdeth/holds'),((' helden ',),' holding '),(('Holde ',),'Hold '),((' hoolde ',' holde '),' hold '),((' houlde,',' holde,'),' hold,'),
                (('HOLINES ',),'HOLINESS '),(('Holinesse',),'Holiness'),(('Holines ',),'Holiness '),((' holynesse',' holinesse',' holynes'),' holiness'),((' holines ',),' holiness '),((' holines,',),' holiness,'),((' holines:',),' holiness:'),
                    ((' HOLI ',),' HOLY '), ((' hooli ',' holie ',' holye ',' holi '),' holy '),((' hooli,',' holye,'),' holy,'),((' hooli.',' holie.'),' holy.'),((' hooli;',' holi;'),' holy;'),
            ((' hoom',),' home'),
            (('honeste','honestye','honestie'),'honesty'), ((' hony',' honie'),' honey'),
                ((' onourid',),' honoured'),(('Honoure','Honor'),'Honour'),((' honor',' onour'),' honour'),((' honoure ',),' honour '),((' honoure,',),' honour,'),((' honoure.',),' honour.'),((' honoure?',),' honour?'),
            ((' hookes',' hokes'),' hooks'),((' hooke ',' hoke '),' hook '),((' hooke.',),' hook.'), ((' hooues',' hoofes',' hoofs',' hoffes'),' hooves'),((' hoofe ',' hoffe '),' hoof '),((' hoofe,',),' hoof,'),
            ((' hopiden',' hopide',' hopid'),' hoped'),((' hopeth',' hopith'),' hopeth/hopes'),((' hopynge',' hopen'),' hoping'),
                ((' hoppinge',),' hopping'),
            ((' hornes',),' horns'),((' horne ',),' horn '),((' horne,',),' horn,'),((' horne.',),' horn.'), ((' hornettes',),' hornets'),
                ((' orrible',' orible'),' horrible'), (('Horrour',),'Horror'),((' horrour',),' horror'),
                (('horsebacke','horsbacke',),'horseback'),(('horsmen',),'horsemen'),((' horsis',),' horses'),((' horese',),' horse'),((' hors,',),' horse,'),((' hors;',),' horse;'),
            (('Hoastes',),'Hosts/Armies'),((' hosts',' hoostes',' hoastes',' hostes',' oostis'),' hosts/armies'),((' host ',' hooste ',' hoste ',' hoast ',' hoost ',' oost '),' host/army '),((' host,',' hooste,',' hoste,',' hoost,',' hoast,',' oost,'),' host/army,'),((' host.',' hoast.',' hoost.',' oost.'),' host/army.'),((' host?',' hoste?',' hoast?',' hoost?'),' host/army?'),((' host:',' hoast:',' hoste:',' hoose:'),' host/army:'),((' host;',' oost;'),' host/army;'),
            ((' hotte ',' hoote ',' hote '),' hot '),((' hoot?',),' hot?'),
            ((' houndis',),' hounds'),
                ((' houres',),' hours'),((' houre',),' hour'), #((' houre ',),' hour '),((' houre,',),' hour,'),((' houre.',),' hour.'),((' houre?',),' hour?'),
                ((' housholder',),' householder'),
                ((' housis',' howsis'),' houses'),((' housse ',' hous ',' hows '),' house '),((' housse',),' house'),((' hous,',' hows,'),' house,'),((' hows.',' hous.'),' house.'),((' hous?',),' house?'),((' hows;',' hous;'),' house;'), (('houssholde','householde','housholde','houshold'),'household'),
            (('Howebeit',),'Howbeit'),(('Hou ','Howe '),'How '),((' hou ',' howe '),' how '),((' howe.',),' how.'),
                ((' houled',),' howled'),((' howlyng',' youlinge'),' howling'), (('Howle ',),'Howl '),((' howle ',' houle '),' howl '),((' howle,',),' howl,'),((' howle.',),' howl.'),((' howle:',),' howl:'),
                ((' howsoeuer',),' howsoever'),
        ((' humilitie',),' humility'),
            ((' hundreth',' hudreth'),' hundredth'),((' houndredes',' hundridis'),' hundreds'),((' hundrede',' hundrid'),' hundred'),
                ((' hungren',),' hungering'),((' hungride',' hungred',' hugred'),' hungered'),((' hungur',' honger',' hungir',' hoger'),' hunger'), (('Hongrie',),'Hungry'),((' hungrie',' hongrie',' hungri'),' hungry'),
                ((' hunteris',),' hunters'), ((' hunteth',' huntith'),' hunteth/hunts'),
            ((' hurlide ',' hurlid '),' hurled '),
                ((' hurtleth',' hurtlith'),' hurtleth/hurtles'),
                ((' hurtfull ',),' hurtful '),((' hirtynge',' hirtyng'),' hurting'),((' hurte ',' hirte '),' hurt '),((' hurte,',),' hurt,'),((' hurte.',' hirt.'),' hurt.'),((' hurte:',),' hurt:'),
            (('hussbande','husbande','housebonde','hosebonde','hosebondi','hosebond','hu?bande'),'husband'),
                ((' huske',),' husk'),
        (('Iacyncte','Iacinct'),'Hyacinth'),((' iacynt',' iacinct'),' hyacinth'),
            ((' ympne',' hymne'),' hymn'),
            ((' hypocrisie',' ypocrisye',' ypocrisie',' ypocrisy'),' hypocrisy'), (('Ypocrytes',),'Hypocrites'),((' ypocrites',' ypocritis'),' hypocrites'), (('hypocriticall ',),'hypocritical '),
            (('Hyssope','Isope'),'Hyssop'),((' hyssope',' hysope',' ysope'),' hyssop'),
    ((' Y ',),' I '),((' Y,',),' I,'),((' Y?',),' I?'),((' Y;',),' I;'),
        ((' Yd',),' Id'), ((' idel ',' ydle '),' idle '), (('Idoles',),'Idols'),((' ydols',' idoles'),' idols'), (('Idoll,',),'Idol,'),((' idole ',' idoll '),' idol '),((' idole,',' idoll,'),' idol,'),
        (('Yf ',),'If '),((' yff ',' yf '),' if '),(('(yf ',),'(if '),
        (('ignoraunce',),'ignorance'),(('ignoraunt','ignoraut'),'ignorant'),
        ((' ymagis',),' images'),((' ymage',),' image'),
                (('imaginatios','ymaginacios'),'imaginations'),(('ymaginacion',),'imagination'), ((' ymagined',),' imagined'),((' imagineth',' ymagineth'),' imagineth/imagines'), ((' ymagion',),' imagining'), ((' ymagin',' ymagyn'),' imagine'),
            (('immediatelye','immediatlye','immediatly'),'immediately'),
            (('impouerished',),'impoverished'),
        ((' ynne ',' yn '),' in '),((' ynne,',),' in,'),((' ynne?',),' in?'),
            ((' encense',' encence',' incese'),' incense'),
            (('enclyned','inclyned'),'inclined'), (('Encline','Enclyne','Inclyne'),'Incline'),((' encline',' enclyne'),' incline'),
                (('encreesside','encreessid','encreased'),'increased'),(('increaseth','encreessith','encressith'),'increaseth/increases'),((' increasinge',' encreessen',' encresyng'),' increasing'), ((' encreesse',' encrease'),' increase'),
            ((' indifferet',),' indifferent'),
                (('indignacioun','indignacion','indignacio'),'indignation'),
                (('vndiscrete',),'indiscrete'),
            ((' inferiour',),' inferior'), ((' infinit,',),' infinite,'),
                    ((' infirmitie:',),' infirmity:'),
                ((' enfourmed',),' informed'), ((' enfourme ',' enforme '),' inform '),
            (('inhabitours','inhabitauntes','inhabitaunts','inhabitantes','inhabitans'),'inhabitants'), (('enhabited',),'inhabited'),(('inhabite ','enhabite '),'inhabit '),
                (('enheritaunce','enheritauce','inheritaunce','inheritauce'),'inheritance'), ((' inheret ',' inherite ',' enherite ',' enheret '),' inherit '),((' inherite,',),' inherit,'),((' inherite.',),' inherit.'),
            ((' iniquites',),' iniquities'),(('iniquitie ','iniquite '),'iniquity '),(('iniquitie,','iniquyte,'),'iniquity,'),(('iniquitie.',),'iniquity.'),(('iniquitie?',),'iniquity?'),(('iniquitie:','iniquite:'),'iniquity:'),(('iniquitie;',),'iniquity;'),
            ((' iniurie:',),' injury:'), ((' iniur',),' injur'),
            ((' inwardes',),' innards'),
                ((' ynnermer',' innermer'),' innermost'),((' ynnere ',),' inner '),
                (('ynnocence','innocencie','innocency','innocens'),'innocence'), ((' innocenti',' innocente',' innocet'),' innocent'), (('vnnoumbrable',),'innumerable'),
            ((' inspyred',),' inspired'),
                ((' instaunce',),' instance'), (('instrumentis',),'instruments'),(('instrumente',),'instrument'),
            (('integritie',),'integrity'), (('interpretacion','interpretaeion'),'interpretation'),(('interprete ',),'interpret '),
            (('inuade',),'invade'),(('inuasion',),'invasion'),
                (('inuention','invencion','inuencion','ynuencio'),'invention'), ((' inuent',),' invent'),
                ((' vnuysible',),' invisible'), ((' inuite',),' invite'),
                ((' inuocation',),' invocation'),
            (('inwardli',),'inwardly'),((' inwarde ',' ynward '),' inward '),
        ((' irone ',' yron ',' yrun ',' yro ',' irun '),' iron '),((' yron,',' irun,'),' iron,'),((' yron.',),' iron.'),((' yron:',),' iron:'),
        (('Ys ',),'Is '),((' ys ',),' is '),((' ys.',),' is.'),
            (('Ilandes','Iland'),'Island'),((' yland',),' island'),
            ((' yssue',),' issue'),
        (('Yt ',),'It '),((' yt ',),' it '),((' yt,',),' it,'),((' yt.',),' it.'),(('(yt ',),'(that '),
        (('Juorie','Yuorie','Yuery','Iuory'),'Ivory'),((' yuorie',' iuorie',' yuory',' iuory',' yuerie',' yuery',' yuer'),' ivory'),
    ((' iawes',),' jaws'),
        (('iealousie','ielousie','gelousie','gelousli'),'jealousy'), (('Ielous',),'Jealous'),((' iealous',' ielous',' gelous'),' jealous'),
            ((' ieopardie',' ieoperdie',' ioperdy'),' jeopardy'),
            ((' jested',' iested'),' jested/joked'),((' jest ',' iest '),' jest/joke '),
            (('Iewels',),'Jewels'),((' iewell',' iewel'),' jewel'),
        ((' ioyning',),' joining'), ((' ioynede',' ioyned',' ioined'),' joined'),((' ioyne ',),' join '), ((' ioints',' ioyntes',' ioynts'),' joints'),((' ioynt',),' joint'),
            (('iourneyed','iourneied'),'journeyed'), (('Iorney',),'Journey'),(('iourneye','iourney','iourneie','iournei','iorney'),'journey'),
            ((' ioyfully',' ioyfuli',),' joyfully'),((' ioyfull',' ioyful',' ioiful'),' joyful'),((' ioiynge',' ioiyng',),' joying/rejoicing'),((' ioyous',),' joyous'),
                (('Ioie ',),'Joy '), ((' ioye ',' ioie ',' ioy '),' joy '),((' ioye,',' ioie,',' ioy,'),' joy,'),((' ioie.',' ioye.',' ioy.'),' joy.'),((' ioye:',' ioy:'),' joy:'),((' ioye;',' ioy;'),' joy;'),
        ((' iubilee ',' jubile '),' jubilee '),((' iubilee,',' jubile,',),' jubilee,'),((' iubilee.',' jubile.',),' jubilee.'),((' jubile:',),' jubilee:'),((' iubilee;',' jubile;',),' jubilee;'),
        ((' demyde ',),' judged '),((' iudging',),' judging'), (('Iudgment',),'Judgement'),(('iugdement','iudgemente','iudgemete','iudgement','iudgmente','judgment','iudgment','iudgemet','iudgmete','iudgmet'),'judgement'),
                ((' iugis',),' judges'),((' iudge',' iuge'),' judge'),(('Iudge','Ivdge'),'Judge'),
            ((' iuice',),' juice'),
            ((' iump',),' jump'),
            ((' ioyncturis',),' junctures'), (('Iuniper',),'Juniper'),((' iuniper',),' juniper'),
            ((' iuri?diction',),' jurisdiction'),
            (('Iustice ',),'Justice '), ((' iustifiede',),' justified'),((' iustifie ',),' justify '), ((' iuste',' iust'),' just'),
    (('Keepers','Keperis',),'Keepers/Watchmen'),((' keepers',' keperis',),' keepers/watchmen'), ((' kepere',' keper'),' keeper'),((' keepest',' kepest',' kepist'),' keepest/keep'),((' keepeth',' kepith',' kepeth'),' keepeth/keeps'),((' kepynge',' kepyng',' keping'),' keeping'), ((' kepten',' kepte'),' kept'), (('Keepe ','Kepe '),'Keep '),((' kepen ',' keepe ',' kepe '),' keep '),((' keepe,',' kepe,'),' keep,'),((' kepe;',),' keep;'),
            ((' kirchife',' kerchiefe'),' kerchief'),
            ((' kettel',),' kettle'),
            ((' keyes',' keies'),' keys'),((' kaye ',' keye '),' key '),
        (('kydeneris','kydneyes','kidneis'),'kidneys'),
        ((' killeth',' kylleth'),' killeth/kills'),((' killidist',' killiden',' killide',' kylled',' kyllide',' kyllid',' killid'),' killed'),((' kyllinge',),' killing'), ((' kil ',),' kill '),((' kyll',),' kill'), #((' kyll,',),' kill,'),((' kyll.',),' kill.'),((' kyll:',),' kill:'),
                ((' kilne',' kylne'),' kiln'),
            ((' kyndle',),' kindle'),((' kyndlide',' kyndelid',' kindeled',' kyndlid'),' kindled'), ((' kindenesse ',' kyndnesse ',' kindenes ',' kindnes ',' kyndnes '),' kindness '),((' kyndnesse,',' kindenesse,',' kindnesse,',' kindnes,',' kyndnes,'),' kindness,'),((' kyndnesse.',),' kindness.'),((' kyndnesse:',),' kindness:'),
                    ((' kynreddes',' kynredis',' kinredis',' kinreds'),' kindreds'),((' kinrede',' kynrede',' kynred',' kinred'),' kindred'), ((' kyndes',' kindes',' kyndis'),' kinds'),((' kynde ',' kinde ',' kyn '),' kind '),((' kinde,',' kynde,'),' kind,'),((' kynde.',' kinde.'),' kind.'),((' kynde:',' kinde:'),' kind:'),((' kynde;',' kinde;'),' kind;'),
                (('Kingdome',),'Kingdom'),(('kingdome','kyngdoom','kyngdome','kyngdom'),'kingdom'),
                    (('Kynges','Kinges'),'Kings'),((' kynges',' kyngis',' kinges',' kingis'),' kings'),(('KYNG ',),'KING '),((' kynge ',' kyng ',' kinge ',' kige '),' king '),(('Kyng,',),'King,'),((' kinge,',' kynge,',' kyng,'),' king,'),((' kynge.',' kinge.',' kyng.'),' king.'),((' kyng?',),' king?'),((' kinge:',' kyng:'),' king:'),((' kyng;',),' king;'),((' kynge)',),' king)'),
                ((' kinsefolke',' kynsfolke',' kinsfolke'),' kinsfolk'), ((' kinsman',' kinseman',' kynysman',' kynesman',' kynsman'),' kinsman/relative'),
                ((' kinne ',' kynne '),' kin '),((' kinne,',' kynne,'),' kin,'),((' kyn.',),' kin.'),((' kyn;',),' kin;'),
            (('Kirjath-jearim','Kiriath-iearim','Kiriathiarim','Cariathiarym'),'Kiryath-yearim'),
            ((' kissiden',' kisside',' kissid',' kyssed',' kiste'),' kissed'), (('Kisse','Kysse'),'Kiss'),((' kisse ',' kysse '),' kiss '),((' kisse,',' kysse,'),' kiss,'),
            ((' kichene',' kitchin',' kechin'),' kitchen'),
        (('kneadinge',),'kneading'),
            (('knelyng',),'kneeling'), (('kneeled','knelide','kneled'),'knelt'), (('kneele ','knele '),'kneel '), (('knewest','knewen','knewe'),'knew'),
        (('kniues','knyues'),'knives'),(('knyfe',),'knife'),
            (('knocke ',),'knock '),(('knocke,',),'knock,'),
                (('Knowest','Knowist'),'Knowest/Know'),(('knowest','knowist','knowst'),'knowest/know'),(('knoweth','knowith'),'knoweth/knows'),(('knowinge','knowynge','knowyng'),'knowing'), (('Knouleche',),'Knowledge'),(('knowlege','knouleche'),'knowledge'), (('knowne','knowun','knowen'),'known'), (('Knowen ','Knowe ',),'Know '),((' knowe ',' woot '),' know '),((' knowe,',),' know,'),((' knowe.',),' know.'),((' knowe?',),' know?'),((' knowe:',),' know:'),((' knowe;',),' know;'),((' knowe)',),' know)'),
    ((' labored',),' laboured'),((' labourest',),' labourest/labour'),((' labouringe',),' labouring'),((' laboures',),' labours'),((' laboure ',' labor '),' labour '),((' laboure,',' labor,'),' labour,'),((' laboure.',),' labour.'),((' laboure?',),' labour?'),
            ((' lackinge',),' lacking'),((' lacke ',),' lack '),((' lacke,',),' lack,'),
            ((' ladde ',),' lad '),((' ladde,',),' lad,'), ((' ladi ',),' lady '),((' ladi;',),' lady;'),
            # laid/lain -- see under lay below
            ((' lambes',' lambren'),' lambs'), (('Lambe',),'Lamb'),((' lomb ',' lambe ',' labe '),' lamb '),((' lambe,',' lomb,',' labe,'),' lamb,'),((' lambe.',' lomb.'),' lamb.'),((' lambe?',' labe?'),' lamb?'),((' lambe:',),' lamb:'),((' lomb;',),' lamb;'),
                (('lamentacioun','lamentacion','lametation'),'lamentation'),(('lamentatio,',),'lamentation,'),
                ((' laumpis',' lampes'),' lamps'),((' lampe ',),' lamp '),((' laumpe,',),' lamp,'),
            ((' landes',' londes',' londis'),' lands'),((' lande ',' loond ',' londe ',' lond ',' lode '),' land '),((' loond,',' lande,',' londe,',' lond,'),' land,'),((' loond.',' lande.',' londe.',' lond.'),' land.'),((' lande?',' lond?'),' land?'),((' lande:',' londe:'),' land:'),((' lande;',' londe;',' loond;',' lond;'),' land;'),((' londe)',),' land)'),
                (('langagis',),'languages'),((' langage',' laguage'),' language'), (('langwischide',),'languished'),
                ((' lanterne',),' lantern'),
            ((' lappe,',),' lap,'),((' lappe:',),' lap:'),
            (('largenesse',),'largeness'),
            (('lasciuiousnesse',),'lasciviousness'),
                ((' lasteth',' lastith'),' lasteth/lasts'),((' lastynge',),' lasting'), ((' laste ',),' last '),((' laste,',),' last,'),
            ((' lattesse',' latisis',' latijs'),' lattice'),
            ((' laught',' lawght'),' laughed'),
            ((' lauer',),' laver'),
            ((' leeueful',' leueful',' laufull',' lawfull'),' lawful'),
                ((' lawes',' lawis'),' laws'),(('Lawe',),'Law'),((' lawe',),' law'),
            ((' layeth',' laieth',' laith'),' layeth/lays'),((' leiynge',),' laying'),
                ((' layed ',' layde ',' laide ',' laied ',' leiden ',' leide ', ' leyd ',' layd '),' laid '),((' laied,',' layde,',' laide,',' layed,',),' laid,'),((' laide.',),' laid.'), ((' lyen ',),' lain '),
                (('Laye ',),'Lay '),((' laye ',' leye ',' laie ',' lai '),' lay '),((' laye,',),' lay,'),((' laye.',),' lay.'),
        ((' leeder',' ledere'),' leader'), (('leadest','laddest','leedist','ledest'),'leadest/lead'),(('leadeth','ledith','ledeth'),'leadeth/leads'), (('Leade ','Lede '),'Lead '),((' leade ',' leede ',' lede '),' lead '),((' leade,',' leed,',' lede,'),' lead,'),((' leed.',),' lead.'),
                ((' leafe ',' leef '),' leaf '),
                ((' leannesse ',),' leanness '),((' leaneth',' leeneth',' lenith'),' leaneth/leans'),((' leane ',' lene '),' lean '),((' leane,',),' lean,'),
                ((' leapinge',' leepynge'),' leaping'),((' lept ',),' leapt '),((' leape ',),' leap '),((' leape,',),' leap,'),
                ((' learned',' lernyde',' lernede',' lerned',' lernid'),' learned/learnt'),((' learnest',' lernest'),' learnest/learn'),((' learneth',' lerneth'),' learneth/learns'),(('learnyng','learninge','lernynge','lernyng'),'learning'),(('Learne ','Lerne '),'Learn '),((' learne ',' lerne '),' learn '),
                ((' leest',),' least'),
                ((' leeuys',' leeues',' leaues',' leves'),' leaves'), ((' leaveth',' leaueth',' leeueth',' leeuith'),' leaveth/leaves'), (('Leaue ',),'Leave '),((' leeuen ',' leeue ',' leaue ',' leue ',' leve '),' leave '),((' leaue.',' leue.'),' leave.'),((' leaue:',),' leave:'),
                    ((' leavened',' leauened',' leuended'),' leavened/risen'),((' leaven',' leauen',' leuen',' leven'),' leaven/yeast'),
            ((' ledden ',' ledde ',' leden ',' leed '),' led '),((' ledde,',),' led,'),
            ((' leften',' leffte',' leeft',' lefte'),' left'),
            ((' legioun',),' legion'), ((' legges',' leggis'),' legs'),
            ((' leysoure',' leysure',' leasure'),' leisure'),
            ((' lende ',),' lend '),
                ((' lengthe ',),' length '),((' lengthe,',),' length,'),
                ((' lentiles',),' lentils'),
            ((' leoparde',),' leopard'),
            ((' leprosie',' lepre'),' leprosy'),
            ((' lesse ',),' less '),((' lesse,',),' less,'), (('Least ',),'Lest '),((' leste ',),' lest '),
            ((' letten ',' leete ',' lete '),' let '),
            (('Leuiathan','Liuiathan'),'Leviathan'), (('Leuytis',),'Levites'),(('Leuit',),'Levit'),((' leuite',),' levite'), (('Leuy ','Leui '),'Levi '),(('Leui,','Leuy,'),'Levi,'),(('Leuy.','Leui.'),'Levi.'),(('Leui:',),'Levi:'), ((' leuyed',),' levied'),((' leuie ',),' levy '),((' leuie.',),' levy.'),
            ((' lewdnesse ',' lewdnes '),' lewdness '),((' lewdnesse.',),' lewdness.'), ((' lewde ',),' lewd '),
        ((' liberall ',),' liberal '), (('lyberte','libertie'),'liberty'), ((' librarie ',),' library '),
            ((' licke ',),' lick '),
            ((' lyers',' liers'),' liars'),((' lier',' lyer'),' liar'),
                ((' lieden',' lyed'),' lied'),((' liest',' lyest'),' liest/lie'),((' lieth',' lyeth',' lyith'),' lieth/lies'),((' ligynge',' lyinge',' lyenge',' lyege'),' lying'),((' lyes ',),' lies '),((' lyes,',),' lies,'),((' lyes.',),' lies.'),((' lyes?',),' lies?'),((' lyes:',),' lies:'),((' lyes)',),' lies)'),((' lye ',),' lie '),((' lye,',),' lie,'),((' lye.',),' lie.'),
            ((' lyffe',' lyfe',' lijf',' liif'),' life'),
                ((' lyfted',),' lifted'),((' lifteth',' lyfteth'),' lifteth/lifts'),((' liftynge',' liftinge'),' lifting'), (('Lyft',),'Lift'),((' lifte ',' lyfte '),' lift '),((' lyft',),' lift'),
            ((' lightlyge',),' lightly'),
                ((' leityngis',' lightenynges',' lyghtnynges',' lightnynges',' lightninges'),' lightnings'),((' lightenynge',' lighteninge',' liytnyng'),' lightning'),
                ((' lightes',' lyghtes',' liytis'),' lights'), (('Liyt ',),'Light '),((' lyght',' liyt',' leit'),' light'),
            (('likenesse','licknesse','liknesse','licnesse'),'likeness'),((' likenes ',),' likeness '), (('Lykewyse','Likewyse'),'Likewise'),(('lykewyse','likewyse'),'likewise'),
                ((' licnede',' licned'),' likened'),((' licken',' likne'),' liken'), ((' likyng',),' liking'), (('Lyke ',),'Like '),((' lyke',' lijk',' lijc'),' like'),
            ((' lillies',' lilyes',' lylies'),' lilies'),((' lillie ',' lilie ',' lilye ',' lylie '),' lily '),((' lillie,',' lilie,',' lylie,',' lilye,'),' lily,'),((' lilie.',),' lily.'),
            ((' limites',),' limits'),
            ((' lynagis',),' lineages'),((' lynage',),' lineage'), ((' lynnynge',' lynnyn',' linnen',' lynnen',' lynnun',' lynun',' lynne'),' linen'),
                ((' lyne',),' line'),
                ((' lynckes',' linkes'),' links'),
                ((' lintell',' lyntel'),' lintel'),
            ((' lionessis',),' lionesses'),((' lionesse ',),' lioness '),((' lyonesse:',),' lioness:'), (('Lyon',),'Lion'),(('Lio,',),'Lion,'), ((' lioun',' lyon'),' lion'),((' lyo:',),' lion:'),
            ((' lippes',' lippis',' lyppes'),' lips'), ((' lippe ',),' lip '),((' lippe,',),' lip,'),
            ((' licour',),' liquor'),
            (('Litle',),'Little'),((' litil',' lytell',' lytle',' litle',' lytil'),' little'),
            (('lyuelode',),'livelihood'), (('liuely',),'lively'), ((' lyueden',' lyuede',' livede',' liued',' lyued'),' lived'),((' liveth',' liueth',' lyueth'),' liveth/lives'),((' liues',' lyues'),' lives'),((' lyuynge',' livynge',' lyuinge',' lyunge',' lyuing',' lyuyng',' liuing',' lyuen'),' living'),((' liue ',' lyue '),' live '),((' liue,',' lyue,'),' live,'),((' liue.',' lyue.'),' live.'),((' liue?',' lyue?'),' live?'),((' liue:',' lyue:'),' live:'),((' liue;',' lyue;'),' live;'),
                ((' liuer',' lyuer',' leuer'),' liver'),
        (('Loe,',),'Lo,'),
            ((' loe ',),' lo '),((' loe,',),' lo,'),
            ((' loafe',' loofe',' loof',),' loaf'),
                ((' lothsome',),' loathsome'), ((' lothed',),' loathed'),((' loth ',),' loathe '),
                ((' looues',' loaues'),' loaves'),
            (('lockesmithes',),'locksmiths'), ((' lockid',),' locked'),((' lockis',' lockes'),' locks'), ((' locke.',),' lock.'),
                ((' locustis',),' locusts'),((' locuste',),' locust'),
            ((' lodginge',),' lodging'),
            ((' loftie',),' lofty'),
            (('Logg ',),'Log '),((' logge ',),' log '),
            ((' loyne',' loine'),' loin'),
            ((' loginge',),' longing'), ((' longe ',' loge '),' long '),((' longe,',' loge,'),' long,'),((' longe.',' loge.'),' long.'),((' longe?',' loge?'),' long?'),((' longe:',' loge:'),' long:'),
            ((' lokide',' loked'),' looked'),((' looketh',' loketh',' lokith'),' looketh/looks'),((' lykynge',' lokynge',' lokinge',' lokyng',' loking'),' looking'),(('Lokyng ',),'Looking '),((' lookes',' lokes'),' looks'),
                    (('Looke','Loke',),'Look'),((' looke ',' loke '),' look '),((' looke,',),' look,'),((' looke.',' loke.'),' look.'),((' loke?',),' look?'),((' looke:',),' look:'),
                ((' loosed',' loosid',' lowsed',' losed'),' loosed/released'),((' looseth',' lowseth'),' looseth/looses/releases'), ((' loosing',' loosyng'),' loosing/releasing'),(('releasinge',),'releasing'), ((' lowse ',),' loose '),((' lowse,',),' loose,'),((' lowse.',),' loose.'),((' lowse:',),' loose:'),
            (('lordshippe','lordschipe','lordschip'),'lordship'), (('Lordis',),'Lord’s'),((' lordes',' lordis'),' lords'),(('Lorde',),'Lord'),(('LORDE',),'LORD'),((' lorde ',),' lord '),((' lorde,',),' lord,'),((' lorde:',),' lord:'),
            ((' loseth',' leesith'),' loseth/loses'),((' leese ',),' lose '), ((' losse ',),' loss '), ((' looste',' loost',' loste'),' lost'),
            (('Loth',),'Lot'), (('Lottis',),'Lots'),((' lottes',' lottis'),' lots'),((' lott ',),' lot '),((' lott,',),' lot,'),
            ((' loude ',' lowde ',' lowd '),' loud '),((' loude,',),' loud,'),
            ((' louelynesse',),' loveliness'),((' louely',),' lovely'), ((' louyeris',),' lovers'),((' louer',),' lover'), ((' louyden',' loueden',' louede',' loued',' louyde',' louyd'),' loved'),((' loveth',' loueth'),' loveth/loves'),((' lovest',' louedist',' louest'),' lovest/love'),((' louinge',' louynge',' louyng',' louing'),' loving'),
                (('Loue ',),'Love '),(('Loue,',),'Love,'), ((' loues',),' loves'),((' louen ',' loue '),' love '),((' loue,',),' love,'),((' loue.',),' love.'),((' loue?',),' love?'),((' loue:',),' love:'),((' loue)',),' love)'),
            ((' lowe ',),' low '),((' lowe,',),' low,'),((' lowe.',),' low.'),((' lowe?',),' low?'),((' lowe:',),' low:'),
                ((' lowere ',),' lower '),((' lowere.',),' lower.'),
        ((' lucke ',),' luck '),
            ((' lumpe ',),' lump '),
            ((' lustfuli',),' lustfully'), ((' lustily',' lustyly'),' lustily/vigorously'), ((' lustes',),' lusts'),
    ((' madnesse',),' madness'),((' madnes ',),' madness '), ((' madde ',' madd '),' mad '),((' madde,',' madd,'),' mad,'),((' madde.',),' mad.'),
                ((' maydest',' maad',' madist',' madst',' makide'),' made'),((' maden ',),' made '),((' maden,',),' made,'),((' maden.',),' made.'),((' maden;',),' made;'),
            (('magistratis',),'magistrates'), ((' magnificall',' magnifical'),' magnificent'), (('magnefiede','magnyfied','magnefied'),'magnified'),(('Magnifie ',),'Magnify '),(('magnifie ','magnyfie ','magnefie '),'magnify '),
            (('Mayden','Mayde'),'Maiden'),((' mayden',),' maiden'), ((' maydes',' maides'),' maids'),((' mayde ',' maide ',' mayd '),' maid '),((' mayde,',' maide,'),' maid,'),
                ((' maymed',),' maimed'),
                (('maynteiner','maynteyner'),'maintainer'), ((' mayntayned',' maynteyned',' mayntened'),' maintained'), (('maintainest','manteynest'),'maintainest/maintain'),(('maintaineth','mainteyneth'),'maintaineth/maintains'), (('Manteyne',),'Maintain'),((' mainteine ',' maintaine ',' mayntayne ',' manteyne '),' maintain '),
                    ((' mayne ',' maine '),' main '),
            ((' makynge',' makinge',' maken'),' making'), ((' makeris',),' makers'),((' makere ',),' maker '),((' makere,',),' maker,'),((' makere?',),' maker?'), ((' makest',' makist'),' makest/make'),((' maketh',' makith',' mekith'),' maketh/makes'),
            ((' malitious',),' malicious'),
            ((' mannus',),' man’s'),((' mas ',),' man’s '),((' ma ',),' man '),((' ma,',),' man,'),
                ((' manifolde ',),' manifold '),
                ((' mankynde',),' mankind'),((' mankinde,',),' mankind,'),
                ((' manere',' maner'),' manner'),
                ((' maslaughter',),' manslaughter'),
                ((' manye ',),' many '),((' manie,',' manye,'),' many,'),((' manie.',' manye.'),' many.'),
            ((' marre ',),' mar '),
                ((' maryner',),' mariner'),
                ((' marckettes',' markettes'),' markets'),
                    ((' markis',),' marks'), ((' marcke ',' marck ',' marke '),' mark '),
                ((' mariage',' maryage'),' marriage'), ((' maried',' maryed'),' married'),((' marrieth',' marieth',' maryeth'),' marrieth/marries'),
                    ((' marrowe',' marow',),' marrow'),
                    ((' marrie ',' marie ',),' marry '),
                (('marueyled','marueiled','mervelled','merveled','marueled','merveyled','marveyled','maruailed','marveled'),'marvelled'), (('Marueylous','Maruelous','Maruelos',),'Marvellous'),(('marueilous','merueilis','marueylous','maruellous','maruelous','meruailous','merueiylis','meruaylous','marvelous','mervelous'),'marvellous'), ((' merueils',),' marvels'), (('Marueyle ','Maruell '),'Marvel '),((' marueile',' merveyle',' maruayle',' maruell',),' marvel'),
                (('Maryes','Maries'),"Mary's/Maria's"),(('Marye','Marie'),'Mary/Maria'),
            ((' masoun',),' mason'),
                ((' maistrie',' maistri'),' mastery'), (('Maister','Maistir','Mayster'),'Master'),((' maister',' maistir'),' master'), ((' mastes',),' masts'),
            ((' matche ',),' match '), ((' mattocke',),' mattock'),
            (('Maiestie',),'Majesty'),((' maiestie',' maiesty',' mageste'),' majesty'),((' mayest',' mayste',' mayst',' maiest',' maist'),' mayest/may'),((' maye ',' maie ',' mai '),' may '),(('(maye ',),'(may '),((' maye.',),' may.'),(('Maye ',),'May '),
        (('Mee ',),'Me '),((' mee ',),' me '),((' mee,',),' me,'),((' mee.',),' me.'),((' mee?',),' me?'),((' mee:',),' me:'),((' mee;',),' me;'),
            ((' medowe',),' meadow'),
                ((' meal ',' meale ',' mele ',' meel '),' meal/flour '),((' meal,',' meale,',' meel,',' mele,'),' meal/flour,'),((' meal.',' meale.',),' meal/flour.'),((' meale:',),' meal/flour:'),((' mele;',),' meal/flour;'),
                    ((' meanynge',),' meaning'), ((' meanes',),' means'),((' meane ',),' mean '),((' meane.',),' mean.'),((' meane?',),' mean?'),
                ((' mesurable',),' measurable'), ((' mesure',),' measure'),
                ((' meetis',' metis',' meates'),' meats'),((' meate ',),' meat '),((' meate,',),' meat,'),((' meate.',),' meat.'),((' meate:',),' meat:'),
            ((' meddlid',' medled'),' meddled'),((' meddleth',' medleth'),' meddleth/meddles'),((' medlyng',),' meddling'),((' medle ',),' meddle '),
                ((' medycine',' medicyn'),' medicine'),
            (('meekenesse','meeknesse','meekenes','mekenesse','mekenes','meknes'),'meekness'),(('meaknes ',),'meekness '),
                    ((' mekely',),' meekly'),((' meeke ',' meke '),' meek '),((' meeke,',),' meek,'),((' meeke.',' meke.'),' meek.'),((' meeke:',' meke:'),' meek:'),((' meeke;',),' meek;'),
                ((' meetyngi',' meetinge',' metinge',' meetyng',' metyng',),' meeting'), ((' meeteth',' meteth'),' meeteth/meets'),((' meete ',' mete '),' meet '),((' meete,',' mete,'),' meet,'),((' meete:',' mete:'),' meet:'),
            (('melodie ',),'melody '),
                ((' meltid',),' melted'),(('meltinge',),'melting'),((' melte ',),' melt '),
            ((' membris',),' members'),
                (('memoriall',),'memorial'), ((' memorie,',),' memory,'),
            ((' mendynge',' mendyng',' mendinge'),' mending'), ((' mens ',),' men’s '), # They don't use apostrophe in Bshps.Gnva,Cvdl, e.g., MRK 15:22
                (('mencion',),'mention'),
            (('marchaundise','marchaundies','marchandise','marchaudise','marchaundie','marchadise','marchaudie'),'merchandise'), (('marchaunte','marchante','marchaunti','marchaunt','marchant','marchat'),'merchant'),
                (('mercifull ','mercyfull '),'merciful '), ((' mersiful',),' merciful'),((' mercifull,',' mercyfull,'),' merciful,'),((' mercifull.',),' merciful.'),((' mercifull?',),' merciful?'),((' mercyfull:',' mercifull:'),' merciful:'),  ((' mercyes',),' mercies'), (('Mercie ',),'Mercy '),((' mercie ',' merci '),' mercy '),((' mercie,',' merci,'),' mercy,'),((' mercie.',' merci.'),' mercy.'),((' mercie:',),' mercy:'),((' mercie;',' merci;'),' mercy;'),
                ((' meritis',),' merits'),
                ((' meryly',),' merrily'),((' merrie ',' merie ',' mery '),' merry '),((' mery,',),' merry,'),((' merrie.',' merie.',' mery.'),' merry.'),((' merrie:',),' merry:'),
            ((' messe ',),' mess '), (('messangeres','messangeris','messaungers'),'messengers'),(('messaunger','messauger','messanger'),'messenger'),
            ((' mette.',),' met.'), ((' metall ',),' metal '),
        (('Michah ','Micha '),'Micah '),
            (('Madianites',),'Midianites'),
                ((' myddil',),' middle'), ((' myddest ',' myddis ',' middest ',' mydst ',' middes ',' myddes ',' middis ',' mids '),' midst '),((' mids,',),' midst,'),
                ((' mydnyght',' mydnight',' mydnyyt'),' midnight'),
            (('mightynesse',),'mightiness'),(('myytili',),'mightily'), (('myytieste',),'mightiest'), ((' myghty ',' mightie ',' myghtie ',' myyti ',' myyty ',' miyti '),' mighty '),((' mightie,',' miyti,'),' mighty,'),((' myyti.',' mightie.'),' mighty.'),((' mightie:',),' mighty:'),((' myyti;',' miyti;',),' mighty;'),
                ((' mightest',' myghtest',' myytist'),' mightest/might'),((' myyte ',' mighte '),' might '),((' myyte;',),' might;'),((' myyten',' miyten',' myght',' myyt',' miyt'),' might'),
            (('myldenesse',),'mildness'),((' mylde ',),' mild '),((' mylde;',),' mild;'),
                ((' mylcke ',' mylck ',' mylke ',' milke ',' mylk '),' milk '),((' mylcke,',' mylck,',' mylke,',' mylk,',' milke,'),' milk,'),((' mylk.',),' milk.'),((' milke:',' mylke:'),' milk:'),((' mylk;',),' milk;'),
            ((' mynded',),' minded'),((' myndefull ',' mindfull ',' mindefull ',' myndfull '),' mindful '),((' myndeful',),' mindful'), ((' myndes',' mindes'),' minds'), (('Mynde ',),'Mind '),((' mynde ',' minde '),' mind '),((' mynde,',' minde,'),' mind,'),((' minde.',' mynde.'),' mind.'),((' minde:',' mynde:'),' mind:'),((' mynde;',),' mind;'),
                (('Myne ','Myn '),'Mine '),((' myn ',),' mine '),((' myn.',),' mine.'),((' myne',),' mine'),
                ((' myngle',),' mingle'),
                ((' ministerie ',),' ministry '),((' ministery',),' ministry'), (('ministred','mynistred','mynystriden','mynistriden','mynystride','mynystrid'),'ministered'),((' ministring',),' ministering'),((' mynystris',),' ministers'),((' mynyster',' mynister',' mynystren',' mynystre'),' minister'),
                ((' minstrell',),' minstrel'),
            ((' myracle',),' miracle'),
                ((' mire ',' myre '),' mire/mud '),((' mire,',' myre,'),' mire/mud,'),((' mire.',' myre.'),' mire/mud.'), ((' miry ',' myrie ',' mirie '),' miry/boggy '),
                    ((' myrth',),' mirth'),
                (('Myrre',),'Myrrh'),((' myrrhe',' myrre'),' myrrh'),
                    (('Myrten',),'Myrtle'),((' mirtis',),' myrtles'),((' mirtle',),' myrtle'),
            ((' miscarying',),' miscarrying'),
                    ((' mischiefe',' myschefe',' meschef'),' mischief'), (('mischieuous','mischeuous'),'mischievous'),
                ((' mysdedes',),' misdeeds'),((' misdeede',' my?dede'),' misdeed'),
                ((' mysery',),' misery'),((' miserie ',),' misery '),((' miserie,',),' misery,'),((' miserie.',),' misery.'),((' miserie:',),' misery:'),
                ((' mysfortune',),' misfortune'),
                ((' myssed',),' missed'),
                ((' myist,',),' mist,'),
                    ((' mistresse ',),' mistress '),((' mistresse,',' mistres,'),' mistress,'),((' mastresse:',),' mistress:'),
            ((' miter',),' miter_hat'), ((' mynuti',' myte'),' mite'),
            ((' medlide',' mixte'),' mixed'),((' mixt ',),' mixed '),((' mixt,',),' mixed,'),
        ((' mocke ',),' mock '),
            ((' moysture',),' moisture'), ((' moiste ',' moyste '),' moist '),
            ((' molte ',),' molten '),((' moulten',),' molten'),
            ((' moneye',' mony',' monei',' monie'),' money'),
                ((' monethis',),' months'), (('Moneth',),'Month'),((' monethe',' moneth'),' month'),
            (('Moones','Mones'),'Moons'),((' moones',),' moons'),(('Moone','Mone'),'Moon'),((' moone ',' mone '),' moon '),(('Moone,',),'Moon,'),((' moone,',),' moon,'),(('Moone:',),'Moon:'),((' moone:',),' moon:'),((' moone;',' mone;'),' moon;'),
            (('Mardochee','Mardocheus'),'Mordecai'),
                (('Moreover','Moreouer','Morouer'),'Moreover/What’s_more'),(('moreover','moreoever','moreouer','morouer','moreuer'),'moreover/what’s_more'), ((' moore ',' moare ',' mowe ',' moe ',' mo '),' more '),
                ((' morninge',' mornynge',' mornyng',' morewe'),' morning'),
                ((' morowe',' morow'),' morrow'),
                ((' morsell',),' morsel'),
                ((' morter,',),' mortar,'),((' morter:',),' mortar:'), (('morgaged',),'mortgaged'),
            (('Moises','Moyses'),'Moses'), ((' moost ',' moste '),' most '),
            ((' mouyte ',),' moth '),
                (('modirles',),'motherless'), ((' modris',),' mothers'),((' moder ',' modir '),' mother '),((' modir,',),' mother,'),((' modir.',),' mother.'),((' modir?',),' mother?'),((' modir;',' moder;'),' mother;'), # don't mess up moderate
            (('Mountayne','Mounteyn','Mountaine','Munteyn'),'Mountain'),((' mountaynes',' moutaynes',' mountaines',' mounteyns',' moutaines',' moutayns'),' mountains'),((' mountayne',' mountaine',' moutayne',' mounteyn'),' mountain'), ((' moute ',' moūt ',' mout '),' mount '),
                (('mourneris',),'mourners'), (('moureneden','mourenyde'),'mourned'), ((' mournynge',' mournyng',' mourninge',' morenynge',' mourenyng',' morenyng'),' mourning'), (('Mourne ',),'Mourn '),((' mornen ',' mourne ',' morne '),' mourn '),((' mornen,',' mourne,',' morne,'),' mourn,'),((' mourne.',),' mourn.'),((' mourne?',),' mourn?'),((' mourne!',),' mourn!'),((' mornen:',' mourne:',' morne:'),' mourn:'),((' mourene;',),' mourn;'),
                ((' mouthes',),' mouths'),((' mouthe ',),' mouth '),
            ((' mouyngi',' mouynge',' mouyng'),' moving'),((' mooued',' mouede',' moued',' mouyd'),' moved'),((' moveth',' mooueth',' moueth'),' moveth/moves'),((' mooue ',' moue '),' move '),((' moue.',),' move.'),
            ((' mowen ',),' mown '),
        ((' myche',' moche',' moch',' muche',' mych',' miche'),' much'),
            (('Mulbery','Molbery'),'Mulberry'),(('mulbery',),'mulberry'), ((' mulis',),' mules'), (('multipliede','multiplyed'),'multiplied'),(('multiplie ','multiplye '),'multiply '),
            (('murthurers','murtherers'),'murderers'),(('murthurer',),'murderer'), ((' murther',' murthur'),' murder'),
                (('murmureth',),'murmureth/murmurs'),(('murmuringe',),'murmuring'),((' murmoure ',' murmure '),' murmur '),((' murmure,',),' murmur,'),
            (('Musick',),'Music'),(('musicke','musick'),'music'), (('musicall ',),'musical '), (('musition',),'musician'),
                ((' musynge',' musyng'),' musing'),
                ((' mustarde',),' mustard'), (('Mustre ',),'Muster '), ((' muste ',),' must '),
        (('Mi ',),'My '),#((' mi '),' my '),
            ((' mysterie ',' misterie '),' mystery '),((' misterie,',' mysterie,'),' mystery,'),((' mistery',),' mystery'),
    ((' nailide',' naled'),' nailed'),((' nailis',' nailes',' nayles',' nales'),' nails'),((' naile ',' nayle ',' nale '),' nail '),((' naile,',),' nail,'),
            ((' nakid',),' naked'), (('nakednesse','nakidnesse'),'nakedness'),(('nakednes ',),'nakedness '),(('nakednes,',),'nakedness,'),(('nakednes.',),'nakedness.'),
            ((' nameli',),' namely'),
            (('Naomy','Naemi'),'Naomi'),
            ((' nappe,',),' nap,'),
            (('Nardus','Narde'),'Nard'),((' narde',),' nard'),
                ((' narower',),' narrower'),((' narowe',' narow'),' narrow'),
            (('Nacioun',),'Nation'),((' nacioun',' nacion'),' nation'), # ((' naciouns',' nacions'),' nations'),
                ((' natiue',' natyue'),' native'),
                (('naturall ',),'natural '),
            ((' nauell',' nauel',' nawle'),' navel'), ((' naues',),' naves'), ((' nauie ',),' navy '),
        ((' neere ',' neare '),' near '),((' neere,',' neare,',' nye,'),' near,'),((' neere.',' neare.'),' near.'),((' neere:',' neare:'),' near:'),((' neere;',' niy;'),' near;'),
            ((' necessitie ',' necessite '),' necessity '),((' necessitie.',),' necessity.'),
                ((' necke',' necki'),' neck'),
            ((' needeful ',' needfull ',' nedefull ',' nedeful '),' needful '),((' nedeful.',),' needful.'),
                (('nedynessis',),'needinesses'), ((' nedynesse',' nedinesse'),' neediness'), ((' needie ',' neady ',' nedi ',' nedy '),' needy '),((' needie,',' needye,',' nedi,'),' needy,'),((' needie.',' nedi.'),' needy.'),((' needie:',),' needy:'),((' nedi;',),' needy;'),
                ((' nedlis',),' needle’s'),((' nedle',),' needle'),
                ((' neded',),' needed'),((' needeth',' nedeth',' nedith'),' needeth/needs'), ((' needes',' nedes'),' needs'),((' neede ',' neade ',' nede '),' need '),((' nede;',),' need;'),
            ((' neiyboresse',' neiyboris',' neghboures',' neghbours',' neyghbours',' neygbours'),' neighbours'),((' neiybore',' neyghbour',' neghboure',' neighbor',' neghbour'),' neighbour'),
                (('nethermost',),'lowest'), # Psa 86:13
                    (('Nether ','Nethir '),'Neither '),((' nenether',' neyther',' nether',' nethir'),' neither'),(('(nether',),'(neither'),
            ((' nephewes',),' nephews'),
            ((' nestes',),' nests'),((' neste ',),' nest '),((' neste:',),' nest:'),
            ((' nettes',' nettis'),' nets'),((' nette ',' nett '),' net '),((' nette,',),' net,'), ((' netle',),' nettle'), ((' networkes',),' networks'),((' networke,',),' network,'),((' networke:',),' network:'),
            (('Neverthelesse ','Neuerthelesse ','Neuertheles ','Netheles '),'Nevertheless '),(('Neuerthelesse,','Neuertheles,','Netheles,'),'Nevertheless,'),(('neuerthelesse','neverthelesse'),'nevertheless'),(('neuertheles ','netheles '),'nevertheless '),(('neuertheles)',),'nevertheless)'), (('Neuer',),'Never'),((' neuere',' neuer'),' never'),
            ((' newli',),' newly'), (('Newe ',),'New '),((' newe ',),' new '),((' newe.',),' new.'),
            ((' nexte',),' next'),
        ((' neer ',' nyer ',' nier '),' nigher/nearer '),((' nyy ',' nye ',' niy '),' nigh/near '),((' neiye,',' niy,',' nyy,'),' nigh/near,'),((' nyy.',' nye.'),' nigh/near.'),((' nye:',),' nigh/near:'),
                ((' nyyti',' niyti',' nyyt',' nyght',' nighte',' niyt'),' night'),
                ((' nyntenthe',),' nineteenth'), ((' nyenth',' nynthe',' nynth'),' ninth'),((' nyntithe',),' ninetieth'),((' ninetie ',' nynetye ',' nynti '),' ninety '), ((' nyne ',),' nine '),
        (('Nai,',),'No,'),((' noo ',),' no '),
            ((' noysed',),' noised'),((' noyse',),' noise'),
            ((' noone ',),' noon '),((' noone,',),' noon,'),
            ((' ner ',' ne '),' nor '), (('Northwarde',),'Northward'),(('northwarde',),'northward'),
            ((' nosethirlis',' nosthryls',' nostrels'),' nostrils'),
            (('noothinge','nothyinge','nothinge','nothynge','nothyng'),'nothing'),
            ((' naught',' nouyt',' nought'),' naught/nothing'),#((' nouyt.',),' naught/nothing.'),
            ((' norisshed',),' nourished'),((' norischen',),' nourishing'),((' norish',),' nourish'),
        (('Nowe ',),'Now '),((' nowe ',),' now '),((' nowe,',),' now,'),((' nowe.',),' now.'),((' nowe:',),' now:'),
        (('noumbriden','noumbride','noumbrid','noumbred','numbred','nombred'),'numbered'),(('numbereth','noumbrith'),'numbereth/numbers'),(('noumbre','nombre','nomber','numbre','nobre'),'number'),
            (('nurschiden','nurschide','nurschid'),'nurtured'), ((' nourtoure',),' nurture'),
            ((' nuttes',),' nuts'),((' nutt ',),' nut '),
    ((' TO ',),' T_o_ '),(('I O N',),'I_O_N'),(('T O B I T',),'T_O_B_I_T'),(('ALSO ',),'ALSO_ '),(('O ',),'Oh '),(('ALSO_ ',),'ALSO '),(('T_O_B_I_T',),'T O B I T'),(('I_O_N',),'I O N'),((' T_o_ ',),' TO '),
        (('Okes',),'Oaks'),((' okes',),' oaks'), (('Oke ',),'Oak '),(('Oke,',),'Oak,'),(('Oke.',),'Oak.'),((' oke ',' ook '),' oak '),((' oke,',' ook,'),' oak,'),((' oke.',' ook.'),' oak.'),((' oke;',' ook;'),' oak;'),((' oke:',),' oak:'),
            ((' oori',' oare'),' oar'),
            ((' oathes',' oothes',' othes',' othis'),' oaths'),((' othe ',' ooth ',' oth '),' oath '),((' othe,',' ooth,'),' oath,'),((' oth:',),' oath:'),
        ((' obediet',),' obedient'), (('obeysaunce','obeysance'),'obeisance'),
                ((' obeieden',' obeiede',' obeied'),' obeyed'),((' obeyeth',),' obeyeth/obeys'),((' obeie ',' obeye ',' obay '),' obey '),((' obeye.',),' obey.'),
            (('oblations','oblacions'),'oblations/offerings/presentations'),(('oblation:',),'oblation/offering/presentation:'),
                (('obscuritie,',),'obscurity,'),
            (('obligacioun',),'obligation'),
                ((' obseruaunce',),' observance'), ((' obseruynge',' observinge',' obseruing'),' observing'), (('Obserue',),'Observe'),((' obserue',),' observe'),
            ((' obtayned',' obteined',' optayned',),' obtained'),(('obtaineth','opteyneth'),'obtaineth/obtains'),((' opteyninge',' obtayning',),' obtaining'),((' opteyne ',' obteyne ',' obteine ',' obtaine ',' optayne ',' obtayne '),' obtain '),
        ((' ocupacioun',),' occupation'), ((' ocupied',' occupyed'),' occupied'),((' occupyenge',' occupienge'),' occupying'),((' occupie ',' occupye '),' occupy '),
        ((' odoures',),' odours'),
        ((' of;',),' off;'),
                ((' offende ',),' offend '),((' offende,',),' offend,'),((' offende.',),' offend.'),
                    (('offryngis','offeringes','offrynges'),'offerings'),((' offerynge',' offeryng',' offeringe',' offringe',' offring',' offryng',' offren'),' offering'),
                        ((' offriden',' offeride',' offride',' offrid',' offred'),' offered'),((' offerest',' offridist'),' offerest/offer'),((' offereth',' offreth',' offrith'),' offereth/offers'), (('Offre ',),'Offer '),((' offre ',' ofre '),' offer '),((' offre,',),' offer,'),
                ((' offyce',),' office'), #((' offycer',),' officer'),
            (('Ofte ','Oft '),'Often '),((' ofte ',' oft '),' often '),((' ofte;',),' often;'),
        ((' oyle ',' oile '),' oil '),((' oyle,',' oile,'),' oil,'),((' oyle.',' oile.'),' oil.'),((' oyle:',' oile:'),' oil:'),((' oile;',' oyle;'),' oil;'), ((' oyled',),' oiled'),
            ((' oynementi',' ointmente',' oyntmente',' oynement',' oyntment'),' ointment'),
        ((' eeld ',' elde ',' eld ',' olde '),' old '),((' eeld,',' olde,'),' old,'),((' olde.',),' old.'),((' olde:',),' old:'),((' olde?',),' old?'),
            (('Oliuete','olivete'),'Olivet'),(('Olyues','Oliues'),'Olives'),((' olyues',' oliues'),' olives'), (('Oliue',),'Olive'),((' olyue',' olyve',' oliue'),' olive'),(('Olive yards',),'Olive-yards'),(('oliveyards','oliue-yards'),'olive-yards'),
        ((' onne?',),' on?'),
            ((' onys,',),' once,'),
                (('Oon ',),'One '),((' oon ',),' one '),((' oon.',),' one.'),((' oon,',),' one,'),((' oon;',),' one;'),
                (('Onely ','Oneli '),'Only '),((' onely ',' onlye ',' oneli ',' oonli '),' only '),((' onely,',' oneli,'),' only,'),((' onely.',),' only.'),((' onely:',),' only:'),
        ((' opynli',),' openly'), ((' openyden',' openede',' openyde',' openned',' openyd'),' opened'),(('openyngis',),'openings'),(('openynge',),'opening'), ((' openeth',' openith'),' openeth/opens'), ((' opene ',' opyn ',' ope '),' open '),((' opyn,',),' open,'),
                ((' operacion',),' operation'),
            ((' opynyouns',),' opinions'),
            ((' opportunite,',' oportunitie,'),' opportunity,'),
                ((' oppressith',),' oppresses'),((' oppresside',' oppressid',' opprest'),' oppressed'),((' oppresse ',),' oppress '),((' oppresse.',),' oppress.'),((' oppressio ',),' oppression '),((' oppressio,',),' oppression,'),((' oppressour',' oppresser'),' oppressor'),
        ((' ortchardes',' orchardes'),' orchards'),((' orcherdi',' orcherd'),' orchard'),
            ((' ordeineden',' ordeyneden',' ordeinede',' ordeined',' ordayned',' ordeynede',' ordeyned',' ordened'),' ordained'),((' ordainest',' ordaynest'),' ordainest/ordain'),((' ordaineth',' ordeneth'),' ordaineth/ordains'), (('Ordeyne ',),'Ordain '),((' ordeynen ',' ordayne ',' ordeyne '),' ordain '),((' ordeine,',),' ordain,'),
                ((' ordred',),' ordered'), ((' ordre',' ordri'),' order'),
                ((' ordinaunce',),' ordinance'),
            ((' orgun',),' organ'),
            ((' orphanes',),' orphans'),((' orphane ',),' orphan '),
            ((' ournementis',' ornamentes'),' ornaments'),
        (('Estriches',),'Ostriches'),((' ostrigis',),' ostriches'),((' ostrig ',),' ostrich '),
        (('Otherwyse',),'Otherwise'),(('Othere','Othir','Wother'),'Other'),((' othere',' othir', ' tothir'),' other'),
        ((' oughte ',' ouyte '),' ought '),
            ((' ourun',' oures'),' ours'), (('Oure ',),'Our '),((' oure ',),' our '),
            ((' outcaste',' out-cast'),' outcast'),
                (('outgoyngi','outgoinge'),'outgoing'),
                ((' outlandishe',' outladish'),' outlandish'),
                ((' outragious',),' outrageous'),
                ((' outwarde',),' outward'),
                (('Ovt ',),'Out '),((' oute ',),' out '),((' oute.',),' out.'),((' oute:',),' out:'),
        ((' ouene,',' oue,'),' oven,'),((' ouene',' oueny',' ouen'),' oven'), # includes plural
                (('Ouer ',),'Over '),((' ouere ',),' over '),((' ouer',),' over'),
                    ((' overcomere',),' overcomer'), (('overcometh','overcommeth'),'overcometh/overcomes'), ((' overcomyng',),' overcoming'), ((' ouercomun',),' overcome'),
                    ((' overflowe ',),' overflow '),((' overflowe,',),' overflow,'),((' overflowe:',),' overflow:'),
                    ((' overlaide',' overlayde',' overlayed',' overlayd'),' overlaid'), # ouer is fixed just above
                    ((' overranne',),' overran'),
                    (('overschadewynge',),'overshadowing'),
                    ((' overthrowen',),' overthrown'),((' overthrewe',),' overthrew'), ((' overthroweth',' overthrowth'),' overthroweth/overthrew'),((' overthrowe ',),' overthrow '), ((' overtooke',),' overtook'),
        ((' owid ',),' owed '),((' oweth',' owith'),' oweth/owes'), ((' owest',' owist'),' owest/owe'),
            (('Owle','Oule'),'Owl'),((' owle',),' owl'),
            ((' awne ',' owne '),' own '),((' owne,',' awne,'),' own,'),((' owne.',' awne.'),' own.'),((' owne:',),' own:'),((' owne;',),' own;'),
        (('Oxen','Ochsen',),'Oxes'),((' oxen',' oxun',' oxis',),' oxes'), ((' oxe ',),' ox '),((' oxe,',),' ox,'), #((' oxun',),' oxen'),
    ((' paiede',' payde',' payed',' payd'),' paid'),
                ((' paynefull ',),' painful '), ((' paines',' paynes'),' pains'),((' payne ',' paine '),' pain '),((' paine,',),' pain,'),((' payne.',),' pain.'),
                    ((' paynted',' peyntid'),' painted'),((' painteth',' paynteth'),' painteth/paints'),
                ((' paire ',),' pair '),
            ((' pallace',' paleis',' pallys'),' palace'), ((' palat ',),' palate '),
                ((' pawmes',' palmes'),' palms'),(('Palme ',),'Palm '),((' paulme ',' palme '),' palm '),((' paulme,',),' palm,'), ((' paulsie',' palsie',' palsye'),' palsy'),
            ((' pannes',' pannys'),' pans'),((' panne,',),' pan,'),((' panne;',),' pan;'),
                ((' cieled',' sieled',' ceiled',' seeled',' syled'),' panelled'),
                ((' panges',),' pangs'),
                ((' panteth',' paunteth'),' panteth/pants'),
            ((' parablis',),' parables'), ((' paradyse ',' paradis '),' paradise '),
                ((' pardone ',),' pardon '),
                ((' parke,',),' park,'),
                ((' partynge',),' parting'), ((' partes',' parties',' partis'),' parts'),((' parte ',),' part '),((' parte,',),' part,'),((' parte.',),' part.'),
                    (('Partener',),'Partner'),((' partener',),' partner'),
            (('Passeouer','Passouer','Pasouer'),'Passover'),(('passeouer','passouer'),'passover'),
                ((' passiden',' passide',' passid'),' passed'),((' passeth',' passith'),' passeth/passes'),((' passynge',),' passing'), (('Passe ',),'Pass '),((' passen ',' passe '),' pass '),((' passe,',),' pass,'),((' passe.',),' pass.'),((' passe?',),' pass?'),((' passe:',),' pass:'),((' passe;',),' pass;'),
                ((' pasturi',),' pasture'),
            ((' pathes',' paches',' pathhis',' pathis'),' paths'), ((' pacience',),' patience'), ((' pacient',' paciet'),' patient'),
                ((' patriarkis',),' patriarchs'),
                ((' patterne',' paterne'),' pattern'),
            (('Pavl',),'Paul'),
            ((' pauement',),' pavement'),((' paued',),' paved'), ((' pauilion',),' pavilion'),
            ((' pawes',),' paws'),
            ((' paye ',),' pay '),((' paye.',),' pay.'),
        ((' pesible',),' peaceable'),(('Pees',),'Peace'),((' pees',),' peace'),
                ((' pearles',),' pearls'),((' pearle,',),' pearl,'),
            ((' peepeth',' pepeth'),' peepeth/peeps'),
            ((' pens,',),' pence,'),((' penne ',),' pen '),
                (('penaunce',),'penance'),
                    (('penniworth','penyworth'),'pennyworth'), ((' penie ',' peny '),' penny '),((' penie,',' peny,'),' penny,'),
                (('pensiveness','pensiuenesse'),'pensiveness/sad_thoughtfulness'),
            (('Puplis',),'Peoples'),(('puplis ',),'peoples '),(('puplis,',),'peoples,'),(('puplis.',),'peoples.'),(('puplis;',),'peoples;'), ((' puple',' pople'),' people'),#((' puple,',),' people,'),((' puple.',),' people.'),((' puple?',),' people?'),((' puple;',),' people;'),
            (('Peradventure','Perauenture'),'Peradventure/Perhaps'),(('peradventure','peraduenture','perauenture'),'peradventure/perhaps'),
                (('perseyuede','perceyued','perceiued','perceaved','perceaued'),'perceived'),(('perceiuing',),'perceiving'),(('Perceaue','Perceave','Perceiue'),'Perceive'),((' witen',' perceiue',' perseyue',' perceaue',' perseiue',' perceave'),' perceive'),
                (('perdition','perdicioun'),'perdition/destruction/punishment'),
                ((' perfitli',' perfitly'),' perfectly'),((' perfaicte ',' perfit '),' perfect '), ((' performyden',' perfourmed'),' performed'),(('perfourmeth ','performeth '),'performeth/performs ' ),((' perfourme ',' performe '),' perform '),((' perfourme,',' performe,'),' perform,'),((' perfourme.',' performe.'),' perform.'),
                ((' periurie',),' perjury'),
                ((' perlous',),' perilous'), ((' perelis',' perels'),' perils'),((' parell ',' perel '),' peril '),((' perel.',),' peril.'),
                    ((' perischiden',' perischide',' perischid'),' perished'),((' perischyng',' perisching',' perischen'),' perishing'), ((' perischen ',' perische ',' perisshe ',' perishe '),' perish '),((' perische,',' perishe,'),' perish,'),((' perische.',' perishe.'),' perish.'),((' perisshe?',' perishe?',' peryshe?'),' perish?'),((' perisshe:',' perishe:'),' perish:'),((' perische;',),' perish;'),
                (('Pherezites','Pheresites'),'Perizzites'),
                ((' perpetuall ',),' perpetual '),((' perpetuall.',),' perpetual.'), ((' perplexitie ',),' perplexity '),((' perplexitie.',),' perplexity.'),
                (('persecucioun','persecucion'),'persecution'), (('persecutours','persecuters'),'persecutors'),
                    ((' personnes',),' persons'),((' personne ',' persen '),' person '),
                    (('persuadeth','perswadeth'),'persuadeth/persuades'),((' perswade',),' persuade'),
                ((' parteyned',' pertayned',' perteined'),' pertained'),((' pertaineth',' perteyneth',' pertayneth',' perteineth',' parteyneth'),' pertaineth/pertains'),((' perteyninge',' pertayninge',' parteyning',' pertayning',' perteining'),' pertaining'), (('PERTEINE',),'PERTAIN'),((' perteynen ',' pertayne ',' pertaine '),' pertain '),
                (('peruersly',),'perversely'), (('peruersnesse ',),'perverseness '),(('peruersnesse,','peruersnes,'),'perverseness,'),((' peruerse',),' perverse'),
                    (('perverteth ','peruerteth '),'perverteth/perverts '), (('peruerte ',),'pervert '),((' peruerte,',),' pervert,'),(('peruert',),'pervert'),
            (('pestylence',),'pestilence'),
            ((' peticion',),' petition'),
        ((' fantum',),' phantom'),
            (('Pharao ','Farao '),'Pharaoh '),(('Pharao,','Farao,'),'Pharaoh,'), (('Fariseis','Farisees','Pharises','pharisees','pharises'),'Pharisees'), (('Philippe',),'Philip'), (('Philistim','Philistyne','Filistei'),'Philistine'), (('phisicians','physicions','physicias'),'physicians'),(('Physition','Physicion','Phisician'),'Physician'),(('phisition','phisicion'),'physician'),
        ((' peaces',' peeces',' peces'),' pieces'),((' peece ',' pece '),' piece '),((' peece,',),' piece,'),
                ((' pearced',' perced'),' pierced'),
                ((' pietie:',),' piety:'),
            (('Pylate',),'Pilate'),(('Pilat ',),'Pilate '),
                (('pilgremage',),'pilgrimage'),((' pilgrymme',' pylgrym',' pilgrime',' pilgrym'),' pilgrim'),
                ((' pileris',' pyllours',' pilers'),' pillars'),((' pyller',' piller',' piler'),' pillar'),
                    ((' pillowe',' pilewi',' pelowe',' pilewe'),' pillow'),
                ((' pilotes',),' pilots'),
            ((' pineth',' pyneth'),' pineth/pines'),((' pyned',),' pined'), (('Pyne',),'Pine'),
                ((' pinnes',),' pins'),
            ((' pypes',),' pipes'),
            ((' pisseth',' pysseth'),' pisseth/pisses'),((' pisse ',),' piss '),
            ((' piyt ',),' pitched '),((' pitche ',),' pitch '),((' pitche.',),' pitch.'),
                    ((' pitifull ',),' pitiful '),((' pitefull)',' pitifull)'),' pitiful)'),
                ((' reuthe ',' pittie ',' pytie ',' pitie ',' pite ',' pyte '),' pity '),((' pitie,',' petie,'),' pity,'),((' pitie.',),' pity.'),((' pitie:',),' pity:'),
                (('pittes','pittis'),'pits'),((' pitte ',' pytte ',' pytt ',' pyt '),' pit '),((' pitte,',' pytte,',' pytt,',' pyt,'),' pit,'),((' pytte.',' pitte.'),' pit.'),
        ((' placis',),' places'),
            ((' plaged',),' plagued'),((' plages',),' plagues'),((' plage ',),' plague '),((' plage,',),' plague,'),((' plage.',),' plague.'),((' plage:',),' plague:'),
                (('playnely','playnly','plainely','pleynli'),'plainly'), ((' plaines',),' plains'),((' playne ',' plaine ',' pleyn '),' plain '),((' plaine.',' playne.'),' plain.'),((' plaine,',' playne,'),' plain,'),((' plaine?',),' plain?'),
                ((' planckes',' plankes'),' planks'),
                    (('plauntidist','plauntide','plauntid'),'planted'), ((' plantes',),' plants'),((' plaunte ',' plante '),' plant '),((' plaunte,',' plante,'),' plant,'),
                (('plastrid',),'plastered'),(('plaister',),'plaster'),
                ((' platis',),' plates'), ((' platere',),' platter'),
                (('pleieri','plaier'),'player'), (('plaied',),'played'),(('pleiynge','playenge','playnge'),'playing'), (('playe ',),'play '),
            (('Pleade ',),'Plead '),((' pleade ',),' plead '),
                    ((' plesauntli',),' pleasantly'),((' pleasaunt',' pleasunt',' plesaunt',' pleasaut'),' pleasant'), ((' pleside',' plesid'),' pleased'),((' pleaseth',' plesith'),' pleaseth/pleases'),((' plesyng',' plesen'),' pleasing'), ((' pleese ',' plese '),' please '),
                (('plentifull ','plentyful '),'plentiful '), ((' plenteuousli',),' plenteously'), ((' pleteousnesse ',' plenteousnes '),' plenteousness '),(('plenteous','plenteuouse'),'plenteous/plentiful'), ((' plentie ',' plentee ',' plente '),' plenty '),
            ((' plat ',),' plot '),((' plat,',),' plot,'), ((' plowemen',),' ploughmen'),((' plowis',),' ploughs'),((' plowe ',),' plough '),((' plowe,',),' plough,'),((' plow',),' plough'),
            ((' pluckte',' pluckt',' plucte'),' plucked'),((' plucke ',),' pluck '),
        ((' pointes',),' points'),((' poynte ',),' point '),((' poynte,',),' point,'),((' poynt',),' point'), ((' poyson ',),' poison '),
            (('policie ',),'policy '), ((' polle',),' poll'), ((' pollutid',' poluted'),' polluted'),
            (('pomegranats','pumgranatis'),'pomegranates'),(('pomgranate','pomgarnate','pumgranate'),'pomegranate'),
                ((' pomp ',' pompe '),' pomp/splendour '),
            ((' pondereth',' pondreth',' podreth'),' pondereth/ponders'),((' pondre ',' podre '),' ponder '), ((' pondis',),' ponds'),
            ((' poole',),' pool'), ((' poore ',' pover ',' povre ',' pore '),' poor '),((' poore.',),' poor.'),((' poore,',),' poor,'),((' poore;',),' poor;'),((' poore:',),' poor:'),
            ((' porchis',),' porches'),((' porche ',),' porch '),((' porche,',),' porch,'), ((' porcion',),' portion'),
                ((' porteri',' portere'),' porter'),((' portes',),' ports'),((' porte ',),' port '),
            (('possessyoun','possessioun'),'possession'),(('possessio:',),'possession:'), (('possessours',),'possessors'), (('possessyd','possest'),'possessed'), (('possesse ',),'possess '),(('possesse.',),'possess.'),(('possesse,',),'possess,'),(('possesse:',),'possess:'),
                    ((' possyble',),' possible'),
                ((' posteritie',' posterite'),' posterity'), ((' postes',' postis'),' posts'), ((' poste ',),' post '),((' poste,',),' post,'),
            (('potsheard','potsherde'),'potsherd'), ((' pottere',),' potter'), ((' pottes',),' pots'),((' pott.',),' pot.'),
            ((' pounde ',),' pound '),((' pounde.',),' pound.'), ((' powred',),' poured'),((' poureth',' powreth'),' poureth/pours'),((' powryng',' powring'),' pouring'), (('Powre ','Poure '),'Pour '),((' powre ',' poure '),' pour '),
            ((' pouertie',' pouerte',' poverte',' pouert'),' poverty'),
            ((' powdir',' pouder'),' powder'),
                ((' poweris',),' powers'),((' pouwer',' pouer'),' power'),
        (('preisiden','praysed','preiside','preisid','preysid'),'praised'),(('preisynge','praysinge','praysing','praysyng','preysyng','preisyng'),'praising'),(('Prayse',),'Praise'),(('prayse','preise','preyse'),'praise'),
                ((' praunsing',' pransing'),' prancing'),
                (('preyeden','preieden','preiede','preyede','praied','prayde','prayd'),'prayed'), (('preieris',),'prayers'), (('Praier ','Preier '),'Prayer '),(('preier','praier','preyer'),'prayer'),(('prayinge','preiynge','preiden','preynge','preyng',),'praying'),((' preye ',' praye ',' preie '),' pray '),((' preye,',' praye,'),' pray,'),((' praye.',' preye.'),' pray.'),((' praye:',' praie:'),' pray:'),((' praye)',),' pray)'),
            (('prechiden','prechide','prechid'),'preached'), (('preachyng','prechynge','preachinge','prechen'),'preaching'), (('preche ','preache '),'preach '),(('preache,','preche,'),'preach,'),(('preche.',),'preach.'),(('preache:',),'preach:'),
                (('preceptes',),'precepts'), ((' preciouse ',' pretious '),' precious '),
                (('predecessour',),'predecessor'), (('predestynacioun',),'predestination'),
                (('preemynence',),'preeminence'),
                ((' prefecti',),' prefect'),
                (('preparedst',),'prepared'),(('preparinge',),'preparing'),
                (('presentes',),'presents'),
                    (('Preserue',),'Preserve'),(('preserue',),'preserve'),
                    (('preassed','preased'),'pressed'),((' pressours',),' presses'), ((' preasse ',' prease ',' presse ',' preace '),' press '),((' preasse,',' prease,',' presse,'),' press,'),((' presse?',),' press?'),
                    (('presumpcion',),'presumption'),
                (('preuailed','preuayled'),'prevailed'),(('prevaileth','preuayleth','preuaileth'),'prevaileth/prevails'),(('preuaile ','preuayle '),'prevail '),(('preuaile,',),'prevail,'),(('preuaile.',),'prevail.'),(('preuayle:','preuaile:'),'prevail:'), (('preuete ',),'prevent '),(('preuent',),'prevent'),
                ((' prei,',),' prey,'), # Wycl Eze 19:3
            (('pryce ','prijs '),'price '),
                (('pryde ',),'pride '),(('pryde,',),'pride,'),
                (('presthode','presthod','preesthod'),'priesthood'),(('preestis','prestis','preestes','prestes','priestes'),'priests'), (('Prieste','Preesti','Preste'),'Priest'),(('prieste','preste','preest','prest',),'priest'),
                (('princesse ',),'princess '), (('Prynces',),'Princes'),(('princis','prynces','pryncis'),'princes'),(('prynce',),'prince'),
                    (('principall ','pryncipall '),'principal '),
                (('priuylie',),'priorly'),
                (('prisouneri','prisoneri','presoner','prysoner'),'prisoner'), ((' prysoun',' prisoun',' pryson',' preson'),' prison'),
                (('priuately','pryuately','pryuatly','pryuely'),'privately'), ((' privy ',' priuie ',' pryuei ',' priuy ',' pryuy ',' preuy ',' prevy '),' privy/private '),((' privy,',' priuie,',' pryuey,'),' privy/private,'), ((' privily',' priuily',' preuely',' priuilie',' priuely',' priueli'),' privily/secretly'),
            (('proceaded',),'proceeded'),(('proceede ','proceade ','procede '),'proceed '),
                    ((' proclaymed',' proclamed'),' proclaimed'),(('Proclaime ','Proclayme ','Proclame '),'Proclaim '),((' proclaime ',' proclayme ',' proclame '),' proclaim '),
                (('prophane',),'profane'), # (('prophaned',),'profaned'),
                    (('profitabli',),'profitably'), (('profitide',),'profited'),(('profiteth','profitith'),'profiteth/profits'),(('profite ',),'profit '),(('profite,',),'profit,'),(('proffet',),'profit'),
                    (('profounde',),'profound'),
                (('prolonge ','prologe '),'prolong '),
                ((' promyse',),' promise'),
                (('profesie ','profecie '),'prophecy '),(('profesie,',),'prophecy,'),
                        (('Prophecie ','Prophesie '),'Prophesy '),(('prophecieden','profesieden','prophesiede','profeciede','profesiede','prophecied'),'prophesied'),(('prophesieth','prophecieth'),'prophesieth/prophesies'),(('prophecienge','profesiynge','prophecying'),'prophesying'),(('prophesie ','prophecie '),'prophesy '),((', prophesie,',', prophecie,'),', prophesy,'),(('and prophecie,',),'and prophecy,'),
                    (('Prophetesse',),'Prophetess'),(('prophetesse',),'prophetess'), (('Prophetes ',),'Prophets '),(('Prophetes.',),'Prophets.'),(('Prophetes:',),'Prophets:'), (('prophetis','profetis','prophetes'),'prophets'),(('prophetis.','prophetes.'),'prophets.'),(('prophetis,','profetis,','prophetes,'),'prophets,'),
                        (('Prophete ',),'Prophet '),(('Prophete.',),'Prophet.'), ((' prophete ',' profete '),' prophet '),((' prophete,',' profete,'),' prophet,'),((' prophete.',),' prophet.'),((' prophete:',),' prophet:'),((' profete;',),' prophet;'),((' prophete?',' profete?'),' prophet?'),
                (('prosperitie','prosperite'),'prosperity'),(('prospere ',),'prosper '),(('prospere,',),'prosper,'),(('prospere.',),'prosper.'),(('prospere?',),'prosper?'),(('prospere:',),'prosper:'),
                (('proteccioun',),'protection'),
                (('proudlie','proudli'),'proudly'),(('proude',),'proud'),
                ((' prooued',' proued',' preued'),' proved'),(('Proue ',),'Prove '),((' prooue ',' proue ',' preue '),' prove '), (('Prouerbes',),'Proverbs'),(('prouerbe','prouerb'),'proverb'),
                    (('prouyded','purueide'),'provided'),(('prouydest',),'providest'),(('prouide','prouyde'),'provide'), (('Prouince',),'Province'),(('prouynci','prouynce','prouince'),'province'), (('prouision','prouysion'),'provision'),
                    ((' prouo',),' provo'), # provocation, provoking, provoked, provoke
        (('Psalmes',),'Psalms'),((' psalmes',' salmes'),' psalms'), (('Psalme',),'Psalm'),((' psalme',),' psalm'),((' salm ',),' psalm '),((' salm.',),' psalm.'), #(('Psalme.',),'Psalm.'),((' psalme,',' salm,'),' psalm,'),((' salm.',),' psalm.'),((' psalme)',),' psalm)'),
            (('Psalterie,',),'Psaltery,'),(('psalterie ',),'psaltery '),(('psalterie,',),'psaltery,'),(('psalterie.',),'psaltery.'),(('psalterie:',),'psaltery:'),
        ((' publique ',),' public '), (('Publicane',),'Publican'), (('puplischid','publysshed','publesshed'),'published'),(('Publishe',),'Publish'),(('publyshe ','publisshe ','puplishe ','publishe '),'publish '),
            ((' puft',),' puffed'),
            ((' punyshedst',' punyschid'),' punished'),((' punishe ',' punysche '),' punish '),((' punishe,',),' punish,'),((' punysh',),' punish'),
            ((' pureste',),' purest'), ((' purenes ',),' pureness '),
                ((' purgeth',' purgith',' porgeth'),' purgeth/purges'),
                (('purificacion',),'purification'), ((' purifie ',),' purify '),((' purifie,',),' purify,'),((' purifie.',),' purify.'),
                ((' purpur',),' purple'), ((' purposide',),' purposed'),
                ((' pourses',),' purses'),((' purs ',),' purse '),
                    ((' pursueris',),' pursuers'),((' pursueden',' pursuede'),' pursued'),((' pursuen',),' pursuing'), (('Sue ',),'Pursue '),
            ((' pusht',),' pushed'),
            ((' puttest ',' puttist '),' puttest/put '),((' putteth ',' puttith '),' putteth/puts '), (('Pvt ',),'Put '),((' puttiden ',' puttide ',' putte '),' put '),
    (('quailes',),'quails'),
            (('quakide',),'quaked'),(('quakyng',),'quaking'),
            (('quantite',),'quantity'),
            (('quarrell ','quarell ','quarel '),'quarrel '), (('quarreris',),'quarries'),
                (('quartre',),'quarter'), (('Quarte,',),'Quart,'),
        (('Queene',),'Queen'),(('queene','quene','queeny'),'queen'),
            (('quenchid','queched'),'quenched'),(('quenche ',),'quench '),(('quenche.',),'quench.'), (('questioun',),'question'),
        (('quike',),'quick/alive'), (('quickely',),'quickly'),(('quyck','quik'),'quick'),(('quicke ',),'quick '),(('quicke,',),'quick,'),(('quicke:',),'quick:'),
            (('quyetnesse',),'quietness'),(('quiete ','quyete '),'quiet '),
            (('quiuer','quyuer'),'quiver'),
    (('Rabi',),'Rabbi'),
            ((' ragige',),' raging'), ((' ragges',),' rags'),
            ((' raile ',' rayle '),' rail '),
                ((' raiment',' rayment',' raymet'),' raiment/clothing'),
                ((' raynbowe',' reynbowe'),' rainbow'),
                    ((' raynie',),' rainy'),((' rayned',),' rained'),((' raineth',' rayneth'),' raineth/rains'), ((' rayne ',' raine ',' reyn '),' rain '),((' raine,',' rayne,'),' rain,'),((' raine.',' rayne.',' reyn.'),' rain.'),((' raine:',' rayne:'),' rain:'),((' raine;',),' rain;'),
                ((' reisiden',' reiside',' reisid',' raysed',' reisen'),' raised'),((' raiseth',' reisith'),' raiseth/raises'), (('Reisynge',),'Raising'),((' reisynge',' reisyng',' raysing'),' raising'), (('Reise ',),'Raise '),((' reise',' reyse',' rayse',' rase'),' raise'), ((' reasinges ',' rasyns '),' raisins '),
            ((' rammes',),' rams'),((' ramme ',' rame '),' ram '),((' ramme.',),' ram.'),((' ramme,',),' ram,'),((' ramme:',),' ram:'),
            ((' runnen ', ' ranne ',' rane '),' ran '),((' ranne,',),' ran,'),((' ranne.',),' ran.'),((' ranne;',),' ran;'),
                ((' ranke',),' rank'),
                ((' raunsome ',' ransome '),' ransom '),((' raunsome:',),' ransom:'),((' ransome;',),' ransom;'),((' raunsum',),' ransom'),
            ((' ratifie ',),' ratify '),((' ratifie)',),' ratify)'),
            (('Rauen',),'Raven'),((' rauen',),' raven'),
                ((' rauished',),' ravished/seized'),((' rauyschinge',' rauyshinge',' rauysching'),' ravishing/seizing'),((' rauysche',),' ravish/seize'),
            ((' razore',' rasoure',' rasour',' raser',' rasor'),' razor'),
        ((' reache ',),' reach '),
                ((' readeth',' redeth',' redith'),' readeth/reads'),((' reade ',' rede '),' read '),
                    ((' readie ',' readye ',' redye ',' redie ',' redi ',' redy '),' ready '),(('(redy ',),'(ready '),((' readie,',' redi,',' redy,'),' ready,'),((' readie.',' redie.',' redy.',' redi.'),' ready.'),((' redy:',),' ready:'),((' redy;',' redi;'),' ready;'),
                (('Realme',),'Realm'),((' realme',' rewme',' reume'),' realm'),
                ((' repyng',),' reaping'), ((' reape ',' reepe ',' repe '),' reap '),((' reape,',),' reap,'),((' reape:',' repe:'),' reap:'),
                ((' reare ',),' rear '),
                ((' resonable',),' reasonable'), (('reasonyng','reasoninge'),'reasoning'), ((' resoun',),' reason'),
            ((' rebellide',),' rebelled'),((' rebell ',),' rebel '),((' rebelle,',),' rebel,'),((' rebell:',),' rebel:'),
            ((' receiveth',' resseyueth',' receaveth',' receaueth',' receiueth'),' receiveth/receives'),((' resseyueden',' resseyuede',' receauedst',' receaved',' receaued',' receiued'),' received'),(('receiuing',),'receiving'),(('Receiue ','Receaue '),'Receive '),((' resseiue',' resseyue',' receave',' receaue',' receiue'),' receive'),
                ((' reccheles',),' reckless'), ((' reckoned',' reckened',' reckned'),' reckoned/counted'), ((' reckoning',' rekenyng',),' reckoning/counting'),((' reckon',' rekynen',),' reckon/count'),
                (('recompence','recopence'),'recompense'), (('reconcyled',),'reconciled'),((' recocile',),' reconcile'), ((' recorde ',),' record '),
                    (('recouered',),'recovered'),(('recouering',),'recovering'),((' recouer ',),' recover '),((' recouer.',),' recover.'),((' recouer:',),' recover:'),
            ((' redde ',' reed '),' red '),((' redde:',),' red:'),
                ((' redemer',),' redeemer'), ((' redemed',),' redeemed'), (('Redeeme ',),'Redeem '),((' redeeme ',' redeme '),' redeem '),((' redeeme,',),' redeem,'),((' redeeme.',),' redeem.'),((' redeeme?',),' redeem?'),((' redeeme:',),' redeem:'),
                ((' redempcioun',' redempcion'),' redemption'),
            ((' reedes',),' reeds'), ((' reele ',' rele '),' reel '),
            (('refourmed',),'reformed'),(('refourme ',),'reform '),
                ((' refreynede',),' refrained'),(('refraine ','refrayne '),'refrain '),
                    ((' refresshed',),' refreshed'),((' refreshe ',),' refresh '),
                ((' refuyt',),' refuge'),
            (('regardest',),'regardest/regard'),((' regarde ',),' regard '),((' regarde,',),' regard,'),
                ((' regencie,',),' regency,'),
                ((' regester ',),' register '),
            ((' rehersid',),' rehearsed'),
            ((' regnyden',' regnyde',' regnede',' regnide',' raigned',' regned'),' reigned'),(('reigneth','raigneth'),'reigneth/reigns'),((' reigne ',' raygne ',' regne ',' raigne ',' raign '),' reign '),((' reigne,',' raigne,',' regne,'),' reign,'),((' reigne.',' raigne.',' regne.'),' reign.'),((' reigne:',),' reign:'), ((' reine',' reyne'),' rein'),
            ((' reiect',),' reject'),
                ((' reioyced',' reioysed'),' rejoiced'),(('rejoicest','reioycest','reioysest'),'rejoicest/rejoice'),(('rejoiceth','reioyceth','reioyseth'),'rejoiceth/rejoices'), (('Reioycing',),'Rejoicing'),((' reioycing',' reioysing'),' rejoicing'),(('Reioyce','Reioyse'),'Rejoice'),((' reioyce',' reioyse'),' rejoice'), #((' reioyce,',' reioyse,'),' rejoice,'),((' reioyce.',' reioyse.'),' rejoice.'),((' reioyce:',),' rejoice:'),((' reioyce?',),' rejoice?'),
            ((' relievest',),' relievest/relieve'),((' relieveth',' releeueth',' relieueth'),' relieveth/relieves'),((' relieue',),' relieve'),
                ((' religioun',),' religion'),
            (('remainest','remaynest'),'remainest/remain'),(('remaineth','remayneth'),'remaineth/remains'),(('remayned',),'remained'),(('remaynynge','remayninge','remayning'),'remaining'),(('remayne ','remaine '),'remain '),(('remayne,','remaine,'),'remain,'),(('remayne.',),'remain.'),(('remayne:','remaine:'),'remain:'),
                ((' remedie ',),' remedy '),((' remedie,',),' remedy,'),
                    ((' remembride',' remembred',' remebred'),' remembered'),(('rememberest','remembrest'),'rememberest/remember'),(('remembereth','remembreth'),'remembereth/remembers'), (('Remembring',),'Remembering'),(('remembryng',),'remembering'), (('Remembre ','Remebre '),'Remember '),((' remembre ',' remebre '),' remember '),((' remembre,',),' remember,'), (('remembraunce','remebraunce','remembrauce','remebrauce'),'remembrance'),
                (('remyssioun','remyssion','remissioun'),'remission'),
                ((' remenauntis',),' remnants'),((' remnaunt',),' remnant'),
                ((' remooued',' remoued',' remouide'),' removed'),((' removeth',' remooueth',' remoueth'),' removeth/removes'),((' remouynge',' remoouing'),' removing'), (('Remooue','Remoue'),'Remove'),((' remooue',' remoue'),' remove'),
            ((' rendred',),' rendered'),
                ((' renued',),' renewed'),((' reneweth',' renueth'),' reneweth/renews'),((' renue ',),' renew '),
                ((' renowmed',),' renowned'),((' renowme ',' renoume ',' renowne '),' renown '),
            ((' reparelid',' repayred'),' repaired'),((' repairinge',),' repairing'),((' repaire ',' repayre ',' reparele '),' repair '),
                ((' repeate,',),' repeat,'),
                    (('repentaunce',),'repentance'), ((' repeted',),' repented'),(('repenteth',),'repenteth/repents'), ((' repente ',),' repent '),((' repente:',),' repent:'),
                (('replenisshed',),'replenished'), (('Replenishe ',),'Replenish '),
                    (('replyed',),'replied'),
                ((' represse ',),' repress '),
                    ((' reproched',),' reproached'),((' reproacheth',' reprocheth'),' reproacheth/reproaches'), (('Reproch',),'Reproach'),((' reproache ',' reproche '),' reproach '),((' reproche.',),' reproach.'),((' reproche:',),' reproach:'),((' reproch',),' reproach'),
                    (('Reproofe',),'Reproof'),((' reproofe',' reprofe'),' reproof'),((' repreuede',' reproued'),' reproved'),((' reproveth',' reproueth'),' reproveth/reproves'),((' repreuynge',),' reproving'),((' reprooue',' reproue',' repreue'),' reprove'),
                ((' reptils',),' reptiles'),
                ((' reputacion',' reputacio'),' reputation'),
            ((' requyre',),' require'), #((' requyred',),' required'),
            ((' reseruing',),' reserving'),((' reserue',),' reserve'), # ((' reserued',),' reserved'),
                ((' resydue',),' residue'),
                (('resistaunce','resistauce'),'resistance'),
                ((' respecteth',),' respecteth/respects'), ((' respecte ',),' respect '),
                ((' restide',),' rested'),((' resteth',' restith'),' resteth/rests'),((' restinge',),' resting'), ((' reest ',' reste '),' rest '),((' reste,',),' rest,'),((' reste;',),' rest;'),
                    ((' restoride',' restorid'),' restored'),(('restoreth','restorith'),'restoreth/restores'),
                    (('restrayned','rstrayned'),'restrained'),(('restraine.','restrayne.',),'restrain.'),
                (('ressurreccioun','resurreccioun','resurreccion'),'resurrection'),
            ((' retaine ',),' retain '),
                (('Returne',),'Return'),((' returne ',),' return '),((' returne.',),' return.'),((' returne,',),' return,'),((' returne?',),' return?'),((' returne:',),' return:'),((' returne;',),' return;'),
            ((' reuealed',' reueiled'),' revealed'),((' revealeth',' reuealeth'),' revealeth/reveals'),((' reueale ',),' reveal '),
                    (('reuelacioun','reuelacion'),'revelation'), ((' reuenge',),' revenge'), (('reuerence',),'reverence'), ((' reuerse ',),' reverse '),
                    (('Reue',),'Reve'),((' reue',),' reve'),
                ((' reuil',' reuyl',' revyl'),' revil'), ((' reuiu',' reuyu'),' reviv'),
                ((' reuol',),' revol'),
            ((' rewardest',),' rewardest/reward'), ((' rewardes ',),' rewards '),((' rewardes.',),' rewards.'), (('Rewarde ',),'Reward '),((' rewarde ',),' reward '),((' rewarde,',),' reward,'),((' rewarde.',),' reward.'),
        ((' ribbes',),' ribs'),
            ((' ritchessis',' richessis',' ryches'),' riches'),((' riche ',' ryche '),' rich '),((' riche,',),' rich,'),((' riche:',),' rich:'),
            ((' ridde ',),' rid '),
                ((' riddil',),' riddle'), ((' rideris',),' riders'),((' ryder',),' rider'), ((' rideth',' rydeth'),' rideth/rides'), ((' rydinge',' ryding'),' riding'),((' ryde ',),' ride '),
            ((' rifeled',),' rifled'),
            (('Righteousnesse','Rightuousnesse'),'Righteousness'),(('Righteousnes ','Rightuousnes '),'Righteousness '),(('riytwisnesse','righteousnesse','rightousnesse','rightuousnesse','rightuosnesse','ryghteousnesse'),'righteousness'),(('righteousnes ','rightuousnes ','ryghteousnes ','rightewesnes '),'righteousness '),(('rightewesnes,','righteousnes,','rightuousnes,'),'righteousness,'),(('Righteousnes.',),'Righteousness.'),(('righteousnes.','rightuousnes.'),'righteousness.'), (('rightewesnes:','righteousnes:','rightuousnes:'),'righteousness:'),(('righteousnes;',),'righteousness;'),
                    (('Rightuous',),'Righteous'),((' ryghteous',' rightuous',' rightous'),' righteous'), ((' righte ',' ryght ',' riyt '),' right '),((' ryght.',' riyt.'),' right.'),((' ryght:',),' right:'),
                ((' ryghtfully',' riytfuli',),' rightfully'),(('riytfulnessis','riytfulnesses'),'rightfulnesses/righteousnesses'),(('riytfulnesse',),'rightfulness/righteousness'),(('riytfulnesse.',),'rightfulness/righteousness.'),(('riytfulnesse;',),'rightfulness/righteousness;'), (('Riytful',),'Rightful'),((' riytful',),' rightful'),
                ((' riytli',),' rightly'),
            ((' rynde ',),' rind '), ((' rynges',),' rings'),((' rynge ',),' ring '),
            ((' rype',),' ripe'),
                ((' rypte ',' ript '),' ripped '),((' ript.',),' ripped.'),
            ((' riseth',' risith',' ryseth'),' riseth/rises'),((' rysinge',' risynge',' rysyng',' rysing'),' rising'), (('Ryse',),'Rise'),((' ryse ',),' rise '),((' ryse,',),' rise,'),((' rysen',' risun'),' risen'),
            ((' ryueris',),' rivers'), (('Riuer','Ryuer'),'River'),((' ryuere',' ryuer',' riuer'),' river'),
        ((' rored',),' roared'),((' roaringe',),' roaring'),((' roare ',' rore '),' roar '),((' roare,',' rore,'),' roar,'),
                ((' rostide',' rosted'),' roasted'),
            ((' robberie ',),' robbery '),((' robberie,',),' robbery,'),((' robberie:',),' robbery:'), ((' robbide',' robbid'),' robbed'),((' robbynge',' robbyng'),' robbing'), ((' robbe ',),' rob '),((' robbe?',),' rob?'),
                ((' roabes',),' robes'),
            ((' rockes',),' rocks'),(('Rocke ',),'Rock '),((' rocke',),' rock'), #((' rocke,',),' rock,'),((' rocke.',),' rock.'),((' rocke:',),' rock:'),
            ((' rods',' roddes'),' rods/staffs'),
                ((' rod ',' rodde ',' rodd '),' rod/staff '),((' rod,',' rodde,',),' rod/staff,'),((' rod.',' rodde.'),' rod/staff.'),((' rod:',' rodde:'),' rod/staff:'),
            (('Roo ',),'Roe/Gazelle '),
            ((' roulled',),' rolled'),((' rolles',),' rolls'),((' rowle ',' roule ',' rolle '),' roll '),((' rolle,',' roule,'),' roll,'),((' roule.',),' roll.'),
            ((' rooffe',' roofe',' roufe',' rofe'),' roof'),
                ((' roume',' rowme',' roome'),' room'),
                ((' roted',),' rooted'),((' rotynge',),' rooting'), ((' rootis',' rootes',' rotes'),' roots'),((' roote ',' rote '),' root '),((' roote,',' rote,'),' root,'),((' roote.',' rote.'),' root.'),
            ((' ropis',),' ropes'),
            ((' risiden ',' roose ',' roos ',),' rose '),((' roos,',),' rose,'),((' roose.',' roos.'),' rose.'), # Protect 'rooster'
            (('rottennesse',),'rottenness'), ((' rotun',),' rotten'),
            (('roudabout',),'roundabout'), (('Roude ',),'Round '),((' rounde ',' roude ',' roud '),' round '),
            ((' roouys',),' rooves'),
            ((' rowes',),' rows'),((' rowe ',),' row '),
            ((' royall ',),' royal '),((' royall.',),' royal.'),
        ((' ruddy',' ruddie',' rodi'),' ruddy/reddish'),
            ((' ruines',),' ruins'),((' ruine ',),' ruin '),((' ruine.',),' ruin.'),
            (('ruleth','rueleth'),'rules'),((' rulinge',' reulyng'),' ruling'), ((' rulars',),' rulers'),
            ((' rumors',),' rumours'),((' rumoure ',),' rumour '), ((' rumpe',),' rump'),
            ((' runneth',' runeth',' renneth'),' runneth/runs'),((' rennynge',' renninge',' runnynge',' runninge',' runnyng'),' running'),(('Runne',),'Run'),((' runne ',' renne '),' run '),((' runne,',),' run,'),((' runne.',' renne.'),' run.'),
            ((' russhed',),' rushed'),((' russhinge',' russhing'),' rushing'),((' rushe ',),' rush '),
    (('Sabbathes',),'Sabbaths'),((' sabatys',' sabatis'),' sabbaths'),(('Sabboth','Saboth'),'Sabbath'),((' sabboth',' saboth',' sabat'),' sabbath'),
            (('sackecloth',),'sackcloth'), ((' sackes',),' sacks'),((' sacke ',' sak '),' sack '),((' sacke,',),' sack,'),((' sacke:',),' sack:'),
                ((' sacrifise',' sacrifici'),' sacrifice'),
            ((' sadde,',),' sad,'), ((' sadlide',' sadled'),' saddled'), (('Saduceis','Saducees','Saduces','Sadduces'),'Sadducees'),
            ((' saaf',),' safe'), ((' safetie',),' safety'),
            ((' seidist',' saydest',' seyden',' seiden',' seide',' seid',' sayde',' sayed',' sayd',' saide', ' seien'),' said'),(('(sayde ','(sayd '),'(said '),(('(sayde:',),'(said:'),
                (('Saintes',),'Saints'),((' sayntes',' saintes',' seyntis'),' saints'),((' saynte',),' saint'),
            ((' saltness',),' saltiness'),((' saltid',),' salted'),((' salte ',),' salt '),
                ((' salutacion',),' salutation'),((' salutid',),' saluted'),
                (('Saluation',),'Salvation'),(('saluation','saluacioun','saluacion','saluacio'),'salvation'),
            (('Samaritanes',),'Samaritans'), ((' saumple',),' sample'), (('Sampson',),'Samson'),
            (('Sanctifie ',),'Sanctify '),((' sanctifie ',' sanctifye '),' sanctify '),((' sanctifie,',),' sanctify,'),
                    (('Sactuary',),'Sanctuary'),(('Sanctuarie ',),'Sanctuary '),(('Sanctuarie,',),'Sanctuary,'),(('Sanctuarie.','Sactuary.'),'Sanctuary.'),(('Sanctuarie:',),'Sanctuary:'),(('sanctuarie ','seyntuarie '),'sanctuary '),(('sanctuarie,','seyntuarie,'),'sanctuary,'),(('sanctuarie.',),'sanctuary.'),(('sanctuarie:',),'sanctuary:'),(('seyntuarie;',),'sanctuary;'),
                ((' sandalies',' sandales'),' sandals'),
                    ((' sondes',),' sands'),((' sande ',' sonde '),' sand '),((' sande.',' sonde.'),' sand.'),
            ((' sappe',),' sap'),
                (('Saphire','Saphyre','Saphir'),'Sapphire'),((' saphyre',' saphir',' safire',' safiri'),' sapphire'),
            ((' sattest ',' saten ',' sate ',' sete '),' sat '),((' sate,',),' sat,'),((' sate:',),' sat:'),
                (('Sathanas','Satanas','Sathan','Satha'),'Satan'),
                ((' satisfaccioun',),' satisfaction'),((' satisfie ',),' satisfy '),
            ((' sauede',' sauyde',' sauyd',' saued',' savyd',' sauid'),' saved'),((' savest',' sauest'),' savest/save'),((' saveth',' saueth'),' saveth/saves'), ((' sauyng',' sauinge',' sauing',' savinge'),' saving'),#(('>sauing',),'>saving'),
                (('Sauioure','Sauiour','Sauior','Sauyor'),'Saviour'),((' savioure',' sauioure',' sauiour',' sauyour',' saveour'),' saviour'),
                ((' sauery',),' savoury'),(('savourest','sauourest','sauerest','sauerist','saverest'),'savourest/savour'),((' sauoures',' sauours'),' savours'), ((' sauoure ',' sauour '),' savour '),
                (('Saue ',),'Save '),((' saue',),' save'), # ((' saue,',),' save,'),((' saue:',),' save:'),((' saue?',),' save?'),
            ((' sawest',),' sawest/saw'),((' sawes ',),' saws '),((' sawes,',),' saws,'), (('Sawe ',),'Saw '),((' sawe ',' sai ',' sayn ',' siyen ',' seyen ',' siy '),' saw '),((' sawe,',),' saw,'),
            ((' sayest',' saiest',' seist'),' sayest/say'),((' seiynge',' sayenge',' sayege',' sayinge',' saynge'),' saying'), ((' saith',' saieth',' sayeth',' seyeth',' seith',' sayth',' seyth'),' saith/says'),(('(saith','(saieth','(sayeth',),'(saith/says'), (('(saye ',),'(say '),(('Seie ','Saye ','Sei '),'Say '),((' seie ',' seye ',' saye ',' saie ',' saiy '),' say '),((' seie,',' saie,',' saye,'),' say,'),((' seie:',' saie:',' saye:'),' say:'),((' seie;',),' say;'),((' saye)',' saie)'),' say)'),
        ((' scabbe',),' scab'),
            ((' scoales',),' scales'), ((' scalpe',),' scalp'),
            (('scarcenesse','scarsenesse'),'scarceness'), ((' skarlet',),' scarlet'),
                (('scattred','scatred','scateriden','scateride','scaterid','scatered'),'scattered'),(('scatterest','scatrest'),'scatterest/scatter'),(('scattereth','scatereth'),'scattereth/scatters'),(('scaterynge','scatering','scateren'),'scattering'),(('scatere ','scatre '),'scatter '),
            ((' scepter',' septre',' ceptre',' cepter'),' sceptre'),
            ((' scoffe ',),' scoff '),
                ((' scorneris',),' scorners'), ((' scornefull',),' scornful'), ((' scorneden',' scornyde',),' scorned'),((' scornynge',' scornyng',),' scorning'), ((' scorne ',' skorne '),' scorn '),((' scorne,',),' scorn,'),((' scorne.',),' scorn.'),((' scorne:',),' scorn:'),
                ((' scourgd',),' scourged'),
            (('Scrybe',),'Scribe'), ((' scryuen',' scribi',' scrybe'),' scribe'), ((' scripturi',' scrypture'),' scripture'),
            ((' scomme ',),' scum '),
            ((' sythe ',' sithe '),' scythe '), # Need final space so doesn't catch 'sithen'
        ((' sealeth',),' sealeth/seals'),((' seelide',),' sealed'),((' seale ',),' seal '),((' seale,',),' seal,'),
                ((' serched',),' searched'), (('Searche ','Serche '),'Search '),((' searche ',),' search '),((' searche,',),' search,'),
                ((' seetis',' seates'),' seats'),((' seete ',' seet ',' seate '),' seat '),((' seate,',' seete,'),' seat,'),((' seate.',' seete.'),' seat.'),((' seete;',),' seat;'),
            ((' secounde ',' seconde ',' secunde '),' second '),((' secounde;',),' second;'), ((' secundarie',),' secondary'),
                ((' secrete',' secreet'),' secret'),
                ((' sikur ',),' secure '),
            ((' sedicio',),' sedition'),
            (('Seest','Seist'),'Seest/See'),((' seest ',' siest ',' seyst '),' seest/see '),((' seeth ',' seeeth ',' seyth '),' seeth/sees '), (('Seynge','Seinge','Seyng'),'Seeing'),((' seynge',' seinge',' seyng',' seing', ' sien'),' seeing'),
                    (('Se ',),'See '),((' seiy ',' se '),' see '),((' siy,',' se,'),' see,'),((' se.',),' see.'),
                ((' seedes',' seedis',' sedes'),' seeds'), ((' seede ',' sede '),' seed '),((' seede,',' sede,'),' seed,'),((' seede.',' sede.'),' seed.'),((' seede:',' sede:'),' seed:'),
                (('Seekest ',),'Seekest/Seek '),((' seekest',' sekest'),' seekest/seek'), ((' seeketh',' seketh',' sekith'),' seeketh/seeks'),((' sekinge',' sekynge',' sekyng'),' seeking'),(('Seeke ','Seke '),'Seek '),((' seken ',' secke ',' seeke ',' seke '),' seek '),((' seeke,',' seke,'),' seek,'),((' seken.',' seeke.',' seke.'),' seek.'),
                ((' semyde',' semed'),' seemed'),((' semeth',),' seemeth/seems'),((' semeli',' semely'),' seemly'), ((' semen ',' seeme ',' seme '),' seem '),
                ((' seyn ',' seene ',' sene ',' sien ',' syen '),' seen '),((' seyn,',' seene,',' sene,',' saien,',' sien,'),' seen,'),((' seene.',' sene.',' seyn.'),' seen.'),((' seene:',),' seen:'),
                ((' seethed',' sethiden',' sethide'),' seethed/boiled'),((' seething',),' seething/boiling'),((' sethe ',),' seethe/boil '),
            ((' seaze',),' seize'),
            ((' silfe ',' silf ',' selfe '),' self '),((' selfe,',' silf,'),' self,'),((' silfe.',' silf.',' selfe.'),' self.'),((' silfe?',' silf?',' selfe?'),' self?'),
                ((' silleris',),' sellers'),((' selleth',' sillith'),' selleth/sells'), ((' selle ',' sille '),' sell '),
                ((' selues',),' selves'),
            ((' symnell ',' symnel '),' semnel/small_loaf '),
            (('Senatour',),'Senator'),((' senatour',),' senator'),
                ((' sendest',' sendist'),' sendest/send'),((' sendeth',' sendith'),' sendeth/sends'), (('Sende ',),'Send '),((' sende ',),' send '),((' sende,',),' send,'),
                ((' senten ',' sente '),' sent '),((' sente,',),' sent,'), (('sentencis',),'sentences'),
            ((' separateth',),' separateth/separates'), ((' seperation',),' separation'), ((' seperate',),' separate'),((' separat.',),' separate.'),
                (('Sepulchres',),'Sepulchres/Tombs'),(('sepulchres','sepulchers','sepulcris','sepulcres'),'sepulchres/tombs'),((' sepulchre',' sepulcre'),' sepulchre/tomb'),
            ((' sermoun',),' sermon'),
                (('serpentis',),'serpents'),(('serpente',),'serpent'),
                (('Seruants',),'Servants'),(('seruauntis','seruauntes','seruautes','servauntes','seruantes','servautes','servantes','seruants','seruats'),'servants'),((' seruaunte',' seruaunt',' servaunt',' seruant',' seruaut',' servaut'),' servant'),
                    ((' servest',' seruest'),' servest/serve'),((' serveth',' serueth'),' serveth/serves'), (('Serue ',),'Serve '),((' serue ',),' serve '),((' serue,',),' serve,'),((' serue.',),' serve.'),((' serue?',),' serve?'),((' serue:',),' serve:'),
                    ((' serueden',' seruyden',' seruyde',' seruede',' serued'),' served'),
                        ((' seruice',' seruyce',' seruyse'),' service'), ((' seruile',' seruyle'),' servile'), ((' seruynge',),' serving'),
                        ((' servitor',' seruitour'),' servitor/servant'), ((' seruitude',' seruage'),' servitude'),
            ((' settinge',' setten'),' setting'), (('Sette ',),'Set '),((' settide ',' sette ',' sett '),' set '),
                ((' setled',),' settled'),
            ((' seuerall',),' several'),
                ((' seuententhe',),' seventeenth'),(('seuenteene','seuentene'),'seventeen'),(('seuenthe','seuenth'),'seventh'),((' seuentithe',),' seventieth'),((' seuentie',' seuenti',' seuentye'),' seventy'),
                    (('Seuene','Seuen',),'Seven'),(('Seue ',),'Seven '),((' seuene',' seuen',' seue'),' seven'),
            ((' sewe ',),' sew '),
        ((' shaddowed',),' shadowed'),((' shadowe ',),' shadow '),((' schadewi',' shadewi',' schadewe',' schadowe',' shadewe',' schadow'),' shadow'),
                ((' schaft',),' shaft'),
                ((' schakun',),' shaken'),((' schake ',),' shake '),
                (('Shal ',),'Shall '),((' shulen ',' schall ',' schal ',' shal '),' shall '),((' shalt ',' schalt ',),' shalt/shall '),
                ((' shamefull ',),' shameful '),((' schame',),' shame'),
                ((' schappli',' schapli',),' shapely'),((' shappe ',),' shape '),
                (('Sharpe ',),'Sharp '),((' scharpe ',' scharp ',' sharpe '),' sharp '),((' sharpe,',),' sharp,'),((' sharpe:',),' sharp:'),
                ((' schauynge',),' shaving'),((' schauen',),' shaven'),((' shaue',),' shave'),
            (('Sche ','Shee '),'She '),((' sche ',' shee '),' she '),
                ((' sheaues',' sheues'),' sheaves'),((' sheafe ',),' sheaf '),((' sheafe,',),' sheaf,'),((' sheafe.',),' sheaf.'),((' sheafe;',),' sheaf;'),
                (('sheddeth','sheadeth'),'sheddeth/sheds'),(('sheddinge','schedinge'),'shedding'),((' schedden ',' shead ',' sheed ',' schede ',' sched '),' shed '),((' sched,',),' shed,'),((' shedde:',),' shed:'),
                (('sheepefolde','sheepfolde','shepefolde','shepefold'),'sheepfold'),
                (('siclis','sicles'),'shekels'),(('Sycle',),'Shekel'),(('shekell','sicle'),'shekel'),
                (('scheepherdis','schepherdis'),'shepherds'),(('Scheepherdi','Shepheard',),'Shepherd'),(('sheepehearde','scheepherde','sheepherde','shepeherde','shepherde','sheephearde','shephearde','sheperde','shepeherd','sheepheard','scheepherd','shepheard'),'shepherd'),
                    # Sheep must be AFTER shepherd, etc.
                    (('Sheepe',),'Sheep'),((' sheepe ',' shepe '),' sheep '),((' sheepe,',' shepe,'),' sheep,'),((' sheepe.',' shepe.'),' sheep.'),((' shepe?',),' sheep?'),((' sheepe:',' shepe:'),' sheep:'),((' sheepe;',),' sheep;'),((' sheepe)',' shepe)'),' sheep)'),((' sheepe-',),' sheep-'),((' scheep',),' sheep'),
                (('Sherifes',),'Sheriffs'),
            ((' shieldes',' scheeldis',' scheldis',' sheldes',' shyldes',' shildes'),' shields'),((' shielde ',' shylde ',' scheeld ',' scheld '),' shield '),((' shielde,',' scheeld,',' shylde,'),' shield,'),((' shielde.',' shilde.'),' shield.'),((' shielde:',' shylde:'),' shield:'),((' shielde;',' scheld;'),' shield;'),
                ((' shyned',),' shined'),(('schyneth','shyneth'),'shineth/shines'),(('schynynge','schynyng','shinyng'),'shining'), ((' schyne',' shyne'),' shine'),#((' shyne.',),' shine.'),((' shyne:',),' shine:'),
                (('shipmaister',),'shipmaster'),((' shippmen',),' shipmen'), (('Schippis',),'Ships'),((' schippis',' shippis',' shippes',' schipis'),' ships'), ((' shyppe',' shyp',' shippe',' shipe',' schip'),' ship'),
            ((' schod',' shood'),' shod'),
                ((' shooes',),' shoes'),((' shooe',' schoo',' shue'),' shoe'),
                ((' shooke',' shoke'),' shook'),
                ((' chepyng',),' shopping'),
                ((' shoore',' shoare'),' shore'), ((' shorun ',' shorne '),' shorn '),((' shorne,',),' shorn,'),
                    (('shortlye',),'shortly'), (('shortned',),'shortened'), ((' shorte ',' schort '),' short '),
                ((' shooteth',),' shooteth/shoots'), (('Shoote','Shute','Schete'),'Shoot'),((' shoote ',' shute ',' shote '),' shoot '), ((' shott ',),' shot '),
                ((' shulder',' schuldre',' schuldur',' schuldri'),' shoulder'),#((' shulder',),' shoulder'),
                    (('Shoulde ','Shulde '),'Should '),(('shouldest','shouldst','shuldest','schuldist'),'shouldest/should'),((' schulden ',' schulen ',' schulde ',' shulde ',' shuld ',' shoulde '),' should '),
                    ((' showt',),' shout'),(('shoute ','showte '),'shout '),(('shoute,',),'shout,'),
                ((' shoued',),' shoved'), ((' shouel',),' shovel'),
                ((' shewest',' schewist'),' shewest/show'),((' sheweth',),' sheweth/shows'),(('shewyng','shewinge','shewing'),'showing'),(('schewide','schewid','shewed'),'showed'),(('Schewe ','Shewe ','Shew '),'Show '),((' schewe ',' shewe ',' shew '),' show '),((' shewe,',),' show,'),
                    ((' showres',' shuwers'),' showers'),
            (('shrewde','schrewid'),'shrewd'), (('shrowd',),'shroud'), (('shrinked',),'shrunk'),(('shrencke','shrinke','shrenke'),'shrink'),
            ((' schit ',),' shut '),
        ((' syckle',' syccle',' syckell',' sikil',' sykell'),' sickle'),
                (('sijknessis','syknessis','sickenesses','syknesses'),'sicknesses'),((' sijknesse ',' syknesse ',' sickenesse ',' sicknesse ',' sikenesse ',' sickeness ',' sickenes ',' sicknes '),' sickness '),((' sicknesse,',' sikenesse,',' sickeness,',' sickenes,'),' sickness,'),((' sicknesse.',' sijknesse.',' siknesse.',' sicknes.'),' sickness.'),((' sijknesse;',),' sickness;'),
                    ((' sicke ',' sijk '),' sick '),((' sicke,',' sijk,'),' sick,'),((' sicke.',' sijk.'),' sick.'),((' sicke?',' sijk?'),' sick?'),((' sicke:',),' sick:'),((' sijk;',),' sick;'),
            ((' sydes',' sidis'),' sides'),((' syde ',),' side '),((' syde,',),' side,'),((' syde.',),' side.'),((' syde:',),' side:'),((' syde;',),' side;'),
            ((' sege ',),' siege '), ((' sieue',' siue',' syue'),' sieve'),
            ((' siffte ',' sifte '),' sift '),
            ((' sighinge',),' sighing'), ((' sygthed',' syghed'),' sighed'),((' sighes',),' sighs'),
                ((' syght ',' sighte ',' siyt '),' sight '),((' sighte,',' siyt,'),' sight,'),((' sighte.',' syght.',' siyt.'),' sight.'),((' syght:',),' sight:'),((' siyt;',),' sight;'), ((' signes',),' signs'),((' signe ',),' sign '),((' signe,',),' sign,'),((' signe?',),' sign?'),((' signe:',),' sign:'),((' signe;',),' sign;'),
                (('signefiyng',),'signifying'), ((' signifie ',),' signify '),
            ((' scilence',' sylence',' silece',' sylece'),' silence'),
                ((' seelk',),' silk'),
                (('siluerlinges','syluerlinges'),'silverlings/silver_coins'),((' siluerne',' siluer',' syluer'),' silver'),
            ((' sinneth',' synneth'),' sinneth/sins'),((' synnynge',),' sinning'), ((' synnefull ',' sinnefull ',' sinfull '),' sinful '), (('sinnemoney','sinne money','sin money'),'sin-money'),(('Synay',),'Sinai'),
                ((' syngeris',' singeris',' singgers',' syngers'),' singers'),((' synger',),' singer'),((' syngynge',' syngen'),' singing'),(('Synge ','Syng '),'Sing '),((' synge ',' syng '),' sing '),((' synge,',),' sing,'),((' synge.',),' sing.'),
                    ((' synguler',),' singular'),
                ((' sinke',' syncke'),' sink'),
            (('symilitude',),'similitude'),
                (('Symount','Symon'),'Simon'),
                ((' symple',),' simple'), (('simplicitie',),'simplicity'),
                ((' simulacion',),' simulation'),
            (('Sens ',),'Since '),((' sence ',' sens '),' since '),
                ((' synewi',' synowe',' sinewe',' sinowe'),' sinew'),
                (('Synneris',),'Sinners'),((' synners',' synneris'),' sinners'),((' synnere',' synner'),' sinner'), ((' synfull',' synful'),' sinful'),((' sinnes',' synnes'),' sins'),((' synneden',' synnede',' synned'),' sinned'),
                    ((' synne ',' sinne '),' sin '),((' synne,',' sinne,'),' sin,'),((' synne.',' sinne.'),' sin.'),((' synne?',' sinne?'),' sin?'),((' synne:',' sinne:'),' sin:'),((' synne;',' sinne;'),' sin;'),
            (('Syr,',),'Sir,'),
            ((' sistris',' systers',' sisterne',' sisteren'),' sisters'),((' sistir',' sistre',' syster'),' sister'),
            ((' sittest',' sittist',' syttest'),' sittest/sit'),((' sitteth',' sittith',' sytteth'),' sitteth/sits'),((' sittynge',' syttinge',' syttyng',' sittinge',' saten'),' sitting'), (('Sitte ','Syt '),'Sit '),((' sitten ',' sitte ',' sitt ',' syt '),' sit '),((' syt,',),' sit,'),((' sitte.',),' sit.'),((' sytte:',),' sit:'),
                ((' liggynge',),' situated'),((' scituate ',),' situate '),
            ((' sixtenthe',' sixtenth'),' sixteenth'),((' sixtithe',),' sixtieth'), (('Sixteene',),'Sixteen'),((' sixteene',' sixtene'),' sixteen'), ((' sixte ',' sixt '),' sixth '),((' sixte,',' sixt,'),' sixth,'), (('Sixti ',),'Sixty '),((' sixtie ',' sixti ',),' sixty '),((' sixtie,',' sixti,'),' sixty,'),((' sixtie.',),' sixty.'),((' sixtie:',),' sixty:'), (('Sixe',),'Six'),((' sixe',),' six'),
        ((' skilfull ',),' skilful '),((' skil ',),' skill '),((' skyll',),' skill'),
            ((' skynnes',' skinnes'),' skins'),((' skynne ',' skyn ',' skinne '),' skin '),((' skinne,',' skynne,',' sknne,',' skiyn,',' skyn,'),' skin,'),((' skinne.',),' skin.'),((' skinne?',),' skin?'),((' skynne:',' skinne:'),' skin:'),
            (('skippide','skypped'),'skipped'),(('scippe ','skyppe '),'skip '),(('skippe;',),'skip;'),
            (('skirtes','skyrtes'),'skirts'),
            ((' scoulles',' sculles',' skulles'),' skulls'),((' skul,',),' skull,'),
            ((' skye',),' sky'),
        ((' slacke',),' slack'),
                (('slayeth','sleeth'),'slayeth/slays/slaughters'), ((' slayne ',' slayn ',' slaine ',' slain ',' sleen '),' slain/killed '),((' slain,',' slayne,',' slaine,',' slayn,'),' slain/killed,'),((' slain.',' slayne.',' slaine.',' slayn.'),' slain/killed.'),((' slain:',' slaine:',' slayne:'),' slain/killed:'),((' slain;',' slaine;',' slayn;'),' slain/killed;'),
                (('sclaundrid',),'slandered/disgraced'),(('slandereth','slaundereth','slaundreth'),'slandereth/slanders'), ((' sclaundre',' sclaundir',' slaunder',' slauder'),' slander'),
                (('slaughted',),'slaughtered'),(('slaughtinge',),'slaughtering'),
                ((' sleynge',' sleyng'),' slaying'), ((' sleye ',' slaye ',' slaie ',' sle '),' slay/kill '),((' slaye,',' sle,'),' slay/kill,'),((' sle.',),' slay/kill.'),
            ((' sleddis',),' sleds'),
                ((' sleepest',' slepest',' slepist'),' sleepest/sleep'),((' sleepeth',' slepeth',' slepith',),' sleepeth/sleeps'), ((' slepinge',' slepynge',' slepyng',' slepen'),' sleeping'), ((' slepten ',' slepte '),' slept '),
                    (('Sleepe ','Slepe '),'Sleep '),((' sleepe ',' slepe '),' sleep '),((' sleepe,',' slepe,'),' sleep,'),((' sleepe.',' slepe.'),' sleep.'),((' sleepe:',' slepe:'),' sleep:'),((' slepe;',),' sleep;'),((' slepe)',),' sleep)'),
                ((' slepte',),' slept'),
                ((' slew ',' slewe ',' slue '),' slew/killed '),((' slew,',' slewe,',' slue,'),' slew/killed,'),((' slew;',),' slew/killed;'),
            ((' slidyng',),' sliding'), ((' slood ',),' slid '),
                ((' slyme ',' sliym '),' slime/mud '),
                ((' slyngi',' slynge',' slyng'),' sling'),
                ((' slipperie',),' slippery'),((' slipte',' slypt',' slipt'),' slipped'),((' slyp ',),' slip '),((' slippe,',),' slip,'),((' slippe.',' slyp.'),' slip.'),
            ((' slouthfull',' slothfull',),' slothful'), ((' slowe ',),' slow '),
            ((' slober',),' slumber'),
        ((' smale ',),' small '),((' smal.',),' small.'),
            ((' smellinge',),' smelling'),((' smelll',),' smell'),((' smel ',),' smell '),
            ((' smytere',),' smiter/striker'), ((' smytten',' smyten',' smytun'),' smitten/struck'),((' smitest',),' smitest/smite/strike'),((' smiteth',' smytith'),' smiteth/smites/strikes'),((' smyting',),' smiting/striking'), (('Smyte',),'Smite/Struck'),((' smytte',' smyte'),' smite/strike'),
            ((' smoake',),' smoke'),
                ((' smoothe ',),' smooth '),
                ((' smotest',),' smotest/smote'),((' smoot ',' smytiden '),' smote '), # Needs space because of 'smooth'
        ((' snaile ',' snayle '),' snail '),((' snale,',),' snail,'),
            ((' neesed ',' nesed '),' sneezed '),
            ((' snowe ',),' snow '),((' snowe,',),' snow,'),((' snowe.',),' snow.'),((' snowe:',),' snow:'),
        ((' soo ',),' so '),((' soo?',),' so?'),
            ((' sokettes',' sockettes'),' sockets'),((' sokett',),' socket'),
            (('Sodome ','zodom '),'Sodom '),
            ((' soeuer ',),' soever '),
            ((' soiourned',),' sojourned'),((' soiourner',),' sojourner'),((' sojourneth',' soiourneth'),' sojourneth/sojourns'),((' soiourne ',),' sojourn '),((' soiourne,',),' sojourn,'),((' soiourne:',),' sojourn:'),
            ((' seelden ',' selden ',' soolde ',' seelde ',' seeld ',' solde ',' seld '),' sold '),((' solde,',' seelde,'),' sold,'),
                    ((' souldiours',),' soldiers'),((' souldiour',' souldier',' soudyer',' soudier',' soudyare'),' soldier'),
                ((' solempnytees',),' solemnities'),((' solempnyte ',' solempnete ',' solempnite ',' solempnytee ',' solemnitie '),' solemnity '),(('solempnytee,',),'solemnity,'), ((' solempne ',' solempe ',' solemne ',' solepne '),' solemn '),
                ((' solitarie',),' solitary'),
                (('solue',),'solve'),(('soluing',),'solving'), # includes dissolved and dissolving
            (('Summen',),'Some'),((' summe ',' sum '),' some '),((' summe,',),' some,'), ((' somthinge',' somthyng'),' something'), ((' somtime',' somtyme',' sumtyme'),' sometime'), (('somwhat','sumwhat'),'somewhat'), ((' somwhere',),' somewhere'),
            (('Sones',),'Sons'),((' sonnes',' sones'),' sons'), (('SONNE ',),'SON '),(('Sonne ','Sone '),'Son '),(('Sonne,','Sone,'),'Son,'),(('Sonne:',),'Son:'),((' sonne ',' sone '),' son '),((' sonne,',' sone,'),' son,'),((' sonne.',' sone.'),' son.'),((' sonne?',' sone?'),' son?'),((' sonne:',),' son:'),((' sone;',),' son;'),((' sonne)',),' son)'),
                ((' songues',' songis'),' songs'),((' songe',),' song'),
            ((' soone ',),' soon '),((' soone,',),' soon,'),((' soone:',),' soon:'),((' soone)',),' soon)'), (('Southsayers',),'Soothsayers'),(('soythsayers',),'soothsayers'),
            ((' sorcerie,',),' sorcery,'),
                ((' sorrowfull ',' soreweful ',' sorowfull ',' soroufull ',' sorowful ',' sorewful '),' sorrowful '),((' sorrowfull,',' sorowfull,',' sorowful,',' sorewful,',' soreuful,'),' sorrowful,'),((' soroufull.',),' sorrowful.'),((' sorowfull?',),' sorrowful?'),((' sorowfull:',),' sorrowful:'),
                    ((' sorewide',),' sorrowed'),((' sorewynge',),' sorrowing'),((' sorewis',' sorrowes',' sorowes',' sorewes'),' sorrows'), (('Sorewe ',),'Sorrow '),((' sorrowe ',' sorewe ',' sorowe ',' sorow '),' sorrow '),((' sorowe,',' sorewe,',' sorow,'),' sorrow,'),((' sorewe.',' sorowe.',' sorow.'),' sorrow.'),((' sorowe?',),' sorrow?'),((' sorowe:',' sorow:'),' sorrow:'),((' sorowe;',' sorewe;'),' sorrow;'),
                ((' sorie ',' sory ',' sori '),' sorry '),((' sory,',' sori,'),' sorry,'),((' sorie.',' sory.',' sori.'),' sorry.'),((' sory:',),' sorry:'),((' sori;',),' sorry;'),
                ((' sortes',),' sorts'),((' sorte ',),' sort '),
            ((' souyten',' souyte',' souyt'),' sought'),
                (('Soule',),'Soul'),((' soulis',),' souls'),((' soule',),' soul'),# ((' soule,',),' soul,'),((' soule.',),' soul.'),((' soule:',),' soul:'),((' soule)',),' soul)'),((' soules',),' souls'),
                ((' soundnesse',),' soundness'), ((' sownyng',),' sounding'), ((' sounde ',' sownde '),' sound '),((' sounde,',),' sound,'),((' sounde.',),' sound.'),((' sounde:',),' sound:'),
                ((' soure',' sowre',),' sour'),
                (('souereynes',),'sovereigns'), ((' souereyn',),' sovereign'),
            ((' sowun ',' sowen ',' sowne '),' sown '),((' sowne,',' sowen,'),' sown,'),((' sowen:',),' sown:'),((' sowun;',),' sown;'),
                ((' soweth',' sowith'),' soweth/sows'),((' sowinge',' sowynge'),' sowing'), (('Sowe ',),'Sow '),((' sowe ',),' sow '),((' sowe,',),' sow,'),((' sowe.',),' sow.'),((' sowe:',),' sow:'),
        ((' spak ',),' spake '),((' spak.',),' spake.'),((' spak;',),' spake;'),
                ((' spanne ',),' span '),
                ((' sparidist',' sparide'),' spared'),
                    ((' sparcle',' sparke',),' spark'),
                    (('Sparrowe',),'Sparrow'),(('sparrowe','sparowe','sparewe','sparow'),'sparrow'),
                ((' spetide',' spette',' spate',' spete'),' spat'),
            ((' spekeri',),' speaker'), ((' speakest',' spekist'),' speakest/speak'),(('speaketh','spekith'),'speaketh/speaks'),(('speakynge','spekynge','speakinge','spekinge','speakyng','spekyng','speking','speken'),'speaking'),
                    (('Speake','Speke'),'Speak'),((' speake ',' speke '),' speak '),((' speake,',' speke,'),' speak,'),((' speake.',' speke.'),' speak.'),((' speake:',),' speak:'),((' speake;',),' speak;'),
                (('spearemen',),'spearmen'),((' speares',' speeris'),' spears'),((' speare ',),' spear '),((' speare,',' spere,'),' spear,'),((' speare.',' spere.'),' spear.'),((' speare:',),' spear:'),((' spere;',),' spear;'),
                ((' specyall ',' speciall '),' special '),
                ((' speaches',' spechis'),' speeches'),((' speache',' speach',' speche'),' speech'),
                    (('speedyly',),'speedily'),((' spedi ',),' speedy '),((' speede ',),' speed '),
                ((' spendeth',' spedeth'),' spendeth/spends'),((' spende ',),' spend '),((' spendid',' spente'),' spent'),((' spet ',),' spent '),
            ((' spyces',),' spices'),((' spyce',),' spice'),
                ((' spyder',),' spider'),
                ((' spyes',),' spies'),((' spieth',' spyeth'),' spieth/spies'),
                (('spirituall ',),'spiritual '), (('spreted ',),'spirited '),((' spirites',' spiritis',' spretes'),' spirits'),(('Spirite','Spiryt'),'Spirit'),((' spirite ',' sprete '),' spirit '),((' spirite,',' sprete,'),' spirit,'),((' spirite.',' sprete.'),' spirit.'),((' spirite:',' sprete:'),' spirit:'),((' sprete)',),' spirit)'),
                    (('spotil','spetil','spettle'),'spittle'), ((' spyt ',),' spit '),((' spyt,',),' spit,'),
            ((' spoyled',),' spoiled'),((' spoyler',),' spoiler'),((' spoileth',' spoyleth'),' spoileth/spoils'),((' spoyling',),' spoiling'),((' spuylis',' spoyles',' spoiles'),' spoils'),((' spoile ',' spoyle '),' spoil '),((' spoile,',' spoyle,'),' spoil,'),((' spoile.',' spoyle.'),' spoil.'),((' spoyle:',),' spoil:'),
                ((' spokun',),' spoken'),((' spaken',),' spoke'),((' spak,',),' spoke,'),
                ((' spoone',' spone'),' spoon'),
                ((' spotte ',' spott '),' spot '),
                ((' spousesse ',),' spouse '),((' spousesse,',),' spouse,'), ((' spoutes',),' spouts'),
            ((' sprange ',' sprong ',' sproge '),' sprang '), ((' spreynt ',),' sprayed '),
                    (('spreadeth','spredeth'),'spreadeth/spreads'),(('spreadyng','spredyng'),'spreading'),((' spredden ',' spredde ',' spreade ',' sprede ',' spreed ',' spred '),' spread '),
                ((' springeth',' spryngeth'),' springeth/springs'),((' sprynginge',),' springing'), ((' springes',),' springs'),((' sprynge',' spryng'),' spring'),((' springe ',),' spring '),
                    ((' sprinckle',' sprenkle'),' sprinkle'),
                ((' sproute ',),' sprout '),
                ((' sprongen',' sprongun',' spronge'),' sprung'),
            ((' spyed',),' spied'),((' spie ',),' spy '),
        ((' squyer ',),' squire '),
        ((' stabli ',),' stably '),((' stabli.',),' stably.'),
                ((' staffe ',' staf '),' staff '),((' staffe,',),' staff,'),((' staf.',),' staff.'),
                ((' stayned',),' stained'),((' staynynge',),' staining'),
                    ((' staires',),' stairs'),
                ((' stalke',),' stalk'),#((' stalke,',),' stalk,'),((' stalke:',),' stalk:'),
                    ((' stalles',),' stalls'),
                (('stambered','stambred'),'stammered'), ((' stampe ',),' stamp '),
                ((' standerde',' standerd'),' standard'),
                    (('stondynge','stondinge','standyng','stodinge'),'standing'),((' standest',' stondest'),' standest/stand'), (('Stondeth',),'Standeth/Stands'),((' standeth',' stondith',' stondeth'),' standeth/stands'), (('Stonde ','Stande '),'Stand '),((' stande ',' stonde '),' stand '),((' stande,',' stonde,'),' stand,'),((' stonde.',),' stand.'),((' stonde?',),' stand?'),((' stonde;',),' stand;'),
                (('Starres',),'Stars'),((' sterris',' sterrys',' starres'),' stars'),((' starre',),' star'),((' sterre.',),' star.'),
                    (('startinge',),'starting'), (('starteled',),'startled'),
                (('staciouns',),'stations'),
                ((' staue',),' stave'),
                ((' staied',' stieden',' stiede'),' stayed'),((' stayes',),' stays'),
            (('stidefast','stidfast','stedfast'),'steadfast'),(('steade',),'stead'), ((' steale ',),' steal '),((' steale,',),' steal,'),((' steale.',),' steal.'),((' steale?',),' steal?'),((' steale:',),' steal:'),
                ((' steele ',' stele '),' steel '),((' steele.',' stele.'),' steel.'), ((' steepe ',),' steep '),
                (('stinch',),'stench'),
                (('Steppe ',),'Step '),((' steppes',' steppis'),' steps'),
                (('sturnenesse',),'sternness'), ((' sterne',),' stern'),
                (('stiward,',),'steward,'),
            ((' stickes',),' sticks'), ((' sticke ',),' stick '),((' sticke,',),' stick,'),((' sticke.',),' stick.'),
                (('styffnecked','styfnecked','stiffnecked','stifnecked'),'stiff-necked'), ((' stiffe ',),' stiff '),
                (('stilnesse',),'stillness'),((' styll ',' stille ',' stil '),' still '), ((' stille,',' styll,',' stil,'),' still,'),((' stille.',' styll.'),' still.'),((' stille;',),' still;'),
                ((' stinketh',),' stinketh/stinks'),((' styncke ',' stinke ',' stynke ',),' stink '),((' stynk',),' stink'),
                ((' sturred',' stiride',' stirid'),' stirred'),((' stiryng',),' stirring'), (('Stirre ','Stire '),'Stir '),((' stirre ',' stire ',' stere '),' stir '),
            ((' stockis',),' stocks'), ((' stocke',),' stock'),
                ((' stollen',),' stolen'),
                ((' stomackes',),' stomachs'),((' stomacke ',' stomac '),' stomach '),((' stomacke,',' stomake,'),' stomach,'),((' stomacke.',' stomak.',),' stomach.'),
                ((' stoonus',' stoonys',' stonys'),' stones'),((' stoone',' stoon'),' stone'), ((' stonie',' stonye'),' stony'),
                ((' stodeth',' stoode',' stonden',' stoden',' stode',' stod'),' stood'),
                    ((' stoles',),' stools'),((' stoole',),' stool'),
                    ((' stouped',' stowped'),' stooped'),((' stoupe',' stowpe'),' stoop'),
                (('stoppid',),'stopped'),(('stoppynge',),'stopping'), ((' stoppe ',' stoope '),' stop '),
                ((' stoare',),' store'),
                    (('Storke',),'Stork'),(('storke',),'stork'),
                    ((' stormie',),' stormy'), ((' stormes',),' storms'),((' storme ',),' storm '),((' storme,',),' storm,'),((' storme.',),' storm.'),((' storme:',),' storm:'),
                    ((' storie ',),' story '),
                ((' stoutnes ',),' stoutness '),
            (('straitnesse','straytnesse'),'straightness'), (('straitened','straitned'),'straightened'),(('strayght','streyght','streight','straite','strayte','streiyt','strate','streit'),'straight'),
                        ((' straytly',),' straitly'),
                    (('Straungers',),'Strangers'),(('straungeris',),'strangers'), (('straunger','strauger','strager'),'stranger'),(('straunge ','strauge '),'strange '),
                        (('strangliden','stranglide','stranglid'),'strangled'),(('strangleth','stranglith'),'strangleth/strangles'),
                    (('strawe ',),'straw '),(('strawe,',),'straw,'),(('strawe:',),'straw:'),
                    (('straied',),'strayed'),
                ((' streames',' streemys',' stremys'),' streams'),((' streame ',),' stream '),((' streame,',),' stream,'),((' streame.',' streem.'),' stream.'),
                    (('streetes','stretis'),'streets'),(('streete','streate','strete'),'street'),
                    (('strengthid','strengthned','strengthed'),'strengthened'), (('strengtheneth','strengthneth'),'strengtheneth/strengthens'), (('strenghten',),'strengthen'), (('strengthis',),'strengths'),(('strengthe ','streygth ','stregth '),'strength '),(('strengthe,','stregth,'),'strength,'),(('strengthe.','stregth.'),'strength.'),(('stregth:',),'strength:'),(('strengthe;',),'strength;'),
                    ((' stretchide',' stretchid'),' stretched'),(('stretcheth','stretchith','strecheth'),'stretcheth/stretches'),(('stretchynge',),'stretching'), (('stretche ',),'stretch '),
                    ((' strewiden ',' strawed ',' strowed '),' strewed '), ((' strowe ',),' strew '),
                ((' striken',),' stricken'),
                    ((' strijf',' stryfe'),' strife'),
                    ((' stringes',' strynges'),' strings'),((' stringe',),' string'),
                    ((' stript ',),' stripped '),((' strype ',' strippe '),' strip '), ((' strypes',),' stripes'),
                    ((' stryuede',),' strived'),((' stryuynge',' stryuyng',' stryvinge',' striuing'),' striving'), (('Stryue',),'Strive'),(('stryve','stryue','striue'),'strive'),
                ((' strokis',),' strokes'),
                    ((' strongere',),' stronger'),((' strongeste',),' strongest'),((' stronge ',' stroge ',' strog ',' stong '),' strong '),((' stronge,',),' strong,'),((' stronge.',),' strong.'),
                    ((' stroue',),' strove'),
                ((' strooke ',' strake '),' struck '),
            ((' stuble',),' stubble'), ((' stubburnly',),' stubbornly'),(('stubborne','stubburne'),'stubborn'),
                (('stucke',),'stuck'),
                (('studiousli',),'studiously'), (('studie ',),'study '),(('studye.',),'study.'), (('studdes',),'studs'),
                (('stuffe',),'stuff'),
                (('stumblest','stomblest'),'stumblest/stumble'),(('stumbleth','stombleth','stomblith'),'stumbleth/stumbles'), ((' stomblinge',),' stumbling'), ((' stomble ',),' stumble '),
                    ((' stumpe ',),' stump '),
        (('subiection','subieccion'),'subjection'),((' subiect',' suget',),' subject'),
                ((' submyt',),' submit'),
                (('substaunce','substauce'),'substance'),
                ((' subtilitie',' subtilty',' sutteltie',' subtiltie'),' subtlety'),((' subtill ',' subtile ',' subtil '),' subtle '),
                ((' suburbes',' subarbis'),' suburbs'),
            ((' successe ',),' success '), ((' succour',' sucoure'),' succour/support/assistance'),
                (('Suche ','Soch '),'Such '),((' soche ',' soch ',' suche ',' siche ',' sich '),' such '),((' suche,',' soch,'),' such,'),((' suche.',),' such.'),((' soch?',),' such?'),((' soche:',),' such:'),
                ((' suckte',' suckt'),' sucked'),((' soukynge',' suckinge',' suckyng'),' sucking'),((' soucke ',' sucke '),' suck '),((' sucke,',),' suck,'),
                ((' suclynges',),' sucklings'),
            ((' sodainlye',' suddainly',' sodeynly',' sodeynli',' sudeynli',' sodainly',' sodaynely',' sodenly',' sodenli',' sodely',' sudenli'),' suddenly'), ((' sodayne ',' sodane '),' sudden '),((' sodayne:',),' sudden:'),
            (('suffereth','suffrith','suffreth'),'suffereth/suffers'),((' suffriden',' suffride',' suffred'),' suffered'),(('sufferynge','suffren'),'suffering'), (('Suffre ',),'Suffer '),((' suffre ',' soffre '),' suffer '),
                (('sufficeth','suffisith'),'sufficeth/suffices'),(('suffysed','suffised'),'sufficed'),
            (('Sommer',),'Summer'),((' sommer',' somer'),' summer'),
            (('Sunne',),'Sun'),((' sunne',),' sun'), #((' sunne ',),' sun '),((' sunne,',),' sun,'),((' Sonne.',),' Sun.'),((' sunne.',),' sun.'),((' sunne?',),' sun?'),((' sunne:',),' sun:'),((' sunne;',),' sun;'),
                ((' suncke',' sunke'),' sunk'), # (('Sunne,',),'Sun,'),
            (('superfluitie','superfluyte'),'superfluity'),
                (('superscripcion',),'superscription'),
                ((' soperis',),' suppers'),((' soper ',),' supper '), (('supplauntide','supplauntid'),'supplanted'), (('supplicacion','supplicacio'),'supplication'),
            ((' surelie ',' surelye '),' surely '), ((' suretie ',' suertie '),' surety '),
                ((' sirname',' syrname'),' surname'),
            (('Shushan','Susan'),'Susa'), # What about Susanna in NT?
                ((' suspende ',),' suspend '), ((' suspicioun',),' suspicion'),
                ((' susteynede',),' sustained'),((' sustaine ',' susteyne '),' sustain '),((' susteyne?',),' sustain?'),
                    ((' sustenauncis',),' sustenances'),((' sustinaunce ',' sustenaunce '),' sustenance '),((' sustenaunce:',),' sustenance:'),
        ((' swaddled',' swadled',' swedled'),' swaddled/wrapped_in_cloth'),
                ((' swalowed',),' swallowed'), ((' swalewis',),' swallows'), ((' swallowe ',' swalowe '),' swallow '),((' swallowe,',' swalowe,'),' swallow,'),
                ((' swarme ',),' swarm '),
            ((' swearest',' swarest'),' swearest/swear'),(('swearinge','sweren'),'swearing'),(('Swere ','Sweare '),'Swear '),((' swere ',' sweare '),' swear '),((' sweare,',' swere,'),' swear,'),
                    ((' swet ',),' sweat '),
                ((' swepe',),' sweep'),
                ((' swarue',),' swerve'),
                (('swettere',),'sweeter'),(('swettest',),'sweetest'), (('swetnesse',),'sweetness'), (('sweetely','swetely'),'sweetly'), (('sweete ','swete '),'sweet '),(('sweete,','swete,'),'sweet,'),(('sweete.','swete.'),'sweet.'),(('sweete:',),'sweet:'),(('swete;',),'sweet;'),
            (('swiftere','swyfter'),'swifter'), (('swiftli',),'swiftly'),(('swifte ','swyft '),'swift '), ((' swymmed',),' swam'),((' swimme ',' swymme '),' swim '),
                ((' swynehearde',' swyneherde',' swineheard'),' swine-herder'),((' swyne',' swyn'),' swine'),
            ((' swerdis',),' swords'),((' sworde',' swearde',' swerde',' swerd'),' sword'),
                (('sworn ','sworne ','sworen '),'sworn/promised '),(('sworn,','sworne,',),'sworn/promised,'),(('sworn:','sworne:',),'sworn/promised:'), ((' sworest',),' sworest/swore/promised'), ((' swoor',),' swore/promised'),
        (('Sycomore',),'Sycamore-fig'),((' sycomore',),' sycamore-fig'),
            (('Synagoge',),'Synagogue'),(('synagoge','synagogi'),'synagogue'),
    ((' tabering',' tabring'),' tabering/beating'), (('tabernaclis',),'tabernacles/tents'),
                ((' tablis',),' tables'),
            ((' taile',),' tail'),
            ((' takun',),' taken'),((' takest',' takist'),' takest/take'),((' taketh',' takith'),' taketh/takes'), (('Takyng',),'Taking'),((' takynge',' takyng'),' taking'),
            ((' tayle ',),' tale '), ((' talentis',),' talents'),
                ((' talketh',),' talketh/talks'),((' talkinge',' talkynge',' talkyng',' talkige'),' talking'),((' talke ',),' talk '),((' talke,',),' talk,'),((' talke.',),' talk.'),
            ((' tarried',' taried'),' tarried/waited'),((' tarrieth',' tarieth',' tarryeth',' taryeth'),' tarrieth/tarries/waits'),((' tarryings',' tariyngis'),' tarryings/waitings'),((' tarrying',' tarienge',' tariege',' tarying'),' tarrying/waiting'), (('Tarry','Tarye','Tarie','Tary'),'Tarry/Wait'),((' tarry ',' tarie ',' tary '),' tarry/wait '),((' tarry,',' tarie,',' tary,'),' tarry/wait,'),((' tarry.',' tarie.',' tary.'),' tarry/wait.'),
            (('taskemasters:',),'taskmasters:'), ((' tastid',),' tasted'), (('Taaste ',),'Taste '),((' taist ',),' taste '),
            ((' taughte',' tauyte',' tauyt'),' taught'), ((' tant',),' taunt'),
        ((' techere',' techeri'),' teacher'),(('teachinge','techinge','techynge','techyng','teching'),'teaching'), (('teachest','techist'),'teachest/teach'),(('teacheth','techith'),'teacheth/teaches'),(('Teache ',),'Teach '),((' teache ',' techen ',' teche '),' teach '),((' teache:',),' teach:'),
                ((' teeris',' teeres',' teares'),' tears'),((' teare ',),' tear '),((' teare,',),' tear,'),
                ((' teats',' teetis',' tetys',' tetis',' teates'),' teats/nipples'),
            ((' tethe ',' teth '),' teeth '),((' teth,',),' teeth,'),((' tethe.',' teth.'),' teeth.'),
            ((' tellest',' tellist'),' tellest/tell'),((' telleth',' tellith'),' telleth/tells'), ((' telle ',' tel '),' tell '),
            ((' temperid',),' tempered'),((' tempre ',),' temper '), ((' tepest',),' tempest'),
                ((' templis',),' temples'),
                (('temptacioun','temptacion','teptacion','tentation','tentacion'),'temptation'), ((' temptiden',' temptid',' temped'),' tempted'),((' temptinge',' tempten'),' tempting'), ((' tempte ',' tepte '),' tempt '),
            ((' tenne ',),' ten '),((' tenne,',),' ten,'), ((' tennauntes',' tenauntes'),' tenants'), ((' tendre',' tendir',' teder'),' tender'), ((' tenthe',),' tenth'),
                ((' tentis',' tentes',' tetes'),' tents'),((' tente ',),' tent '),
            ((' termes',),' terms'),((' terme ',),' term '), ((' terrour',),' terror'),
            (('Testamente',),'Testament'),((' testamente',),' testament'), (('testifie ','testifye ','testyfye '),'testify '), (('testimoniall',),'testimonial'), (('Testimonie,',),'Testimony,'),(('testimonie ',),'testimony '),(('testimonie,',),'testimony,'),
        ((' thankfull ',),' thankful '),(('thankefull.','thankfull.'),'thankful.'),
                    ((' thaked',),' thanked'), (('Thankes',),'Thanks'),(('thanckes','thankes','thakes'),'thanks'),(('thanke ',),'thank '),
                (('Thilke ',),'That '),((' thilke ',),' that '),
            # (('The',),'The'),
            ((' y<sup>t</sup>',),' that'),((' y<sup>e</sup> ',),' the '),
                ((' thee ',),' thee/you '),((' thee,',),' thee/you,'),((' thee.',),' thee/you.'),((' thee?',),' thee/you?'),((' thee:',),' thee/you:'),((' thee;',),' thee/you;'),((' thee)',),' thee/you)'),
                (('Theftes',),'Thefts'),(('theeft','thefte','thefti'),'theft'),
                ((' theyr ',),' their '),
                # ((' hem ',' thē '),' them '),((' hem,',' the,'),' them,'),((' hem.',' the.'),' them.'),
                    ((' thē ',),' them '),((' thē,',' the,'),' them,'),((' the.',),' them.'),
                    ((' the:',' tho:'),' them:'),((' tho;',),' them;'),
                    (('themselues','theselues'),'themselves'),
                (('Thanne ',),'Then '),((' thanne ',),' then '),((' thanne?',),' then?'), ((' thennus',),' thence'),((' thens ',' thece '),' thence '),((' thece,',),' thence,'),((' thece.',),' thence.'),
                (('Ther ',),'There '),((' ther ',),' there '), ((' therafter',),' thereafter'), ((' therby',),' thereby'),((' therof',),' thereof'),((' theron',),' thereon'),
                    (('Therefoe','Therfore','Therfor'),'Therefore'),((' therfore',' therfor'),' therefore'), ((' therto',),' thereto'),
                    ((' therwith',),' therewith'),
                (('Thei ',),'They '),((' thei ',),' they '),((' thei,',),' they,'),((' thei.',),' they.'),((' thei?',),' they?'),((' thei;',),' they;'),
                ((' thes ',),' these '),
            (('Thi ',),'Thy '),
                (('Thicke ',),'Thick '),((' thicke ',' thycke '),' thick '),((' thicke,',),' thick,'),
                ((' thieues',' theeues',' theves',' theues',' theuys'),' thieves'),((' thiefe',' theefe',' theef',' thefe'),' thief'),
                ((' thighes',' thies'),' thighs'),((' thygh ',),' thigh '),
                ((' thynne ',' thinne '),' thin '),
                    (('Thyne ',),'Thine/Your '),((' thine ',' thyne ',' thyn '),' thine/your '),((' thyne,',),' thine/your,'),((' thyne.',),' thine/your.'),((' thyne?',),' thine/your?'),
                    (('Thingis',),'Things'),((' thinges',' thingis',' thynges',' thiges'),' things'),((' thinge',' thynge',' thyng',' thige'),' thing'),
                    (('Thynkest',),'Thinkest/think'),((' thinkest',),' thinkest/think'),((' thinketh',),' thinketh/thinks'),((' thenkynge',' thenkyng'),' thinking'), (('Thinke ','Thynke '),'Think '),((' thincke ',' thynke ',' thenken ',' thenke ',' thinke '),' think '),((' thinke,',),' think,'),((' thinke)',),' think)'),
                    ((' thys ',),' this '),
                ((' thridde',' thyrde',' thirde',' thryd'),' third'),
                    ((' thirstide',),' thirsted'),((' thirstynge',' thristen'),' thirsting'),((' thirstie',' thirstye'),' thirsty'), ((' thirste ',),' thirst '),((' thirste,',),' thirst,'),((' thyrste.',),' thirst.'),((' thurst',' thyrst',),' thirst'),
                    (('thrittenthe',),'thirteenth'), ((' thirteene',),' thirteen'), (('threttithe','thrittithe','thirtith'),'thirtieth'), (('Thirtie ',),'Thirty '),(('thretti ','thirtie ','thirtye ','thritti '),'thirty '),(('thirtie,','thritti,'),'thirty,'),(('thirtie.',),'thirty.'),(('thirtie:',),'thirty:'),
                (('thither','thidur','thidir','thyther'),'thither/there'),
            (('thwong',),'thong'),
                ((' thorne',),' thorn'),
                ((' thoose ',' thoo ',' tho '),' those '),((' tho,',),' those,'),((' tho.',),' those.'),
                (('Thou ',),'Thou/You '),((' thou ',),' thou/you '),((' thou,',),' thou/you,'),#((' thou<',),' thou/you<'),
                    (('Thouy ',),'Though '),((' thouy ',),' though '),
                        ((' thoughtest',),' thoughtest/thought'), ((' thoughtes',' thouytis'),' thoughts'),((' thoughtes ',),' thoughts '),((' thouyten',' thouyte',' thoughte',' thouyt'),' thought'),#((' thoughte,',' thouyte,'),' thought,'),((' thoughte:',),' thought:'),
                        (('thousyndis',),'thousands'),(('thousynde','thousande'),'thousand'),
            ((' threede',' threed'),' thread'), (('threteneden','thretneden','thretenede'),'threatened'),(('threatning',),'threatening'), ((' thre ',),' three '),((' thre,',),' three,'),((' thre:',),' three:'),
                    (('thresholde','threisfold'),'threshold'),
                        (('threshest','throssheth'),'threshest/threshes'), (('threischid',),'threshed'), (('threischyng','throischun','thresshing','treshing'),'threshing'),
                    (('threwe',),'threw'),
                (('thrise','thries','thryse'),'thrice'),
                ((' throtes',),' throats'),((' throate ',' throte '),' throat '),((' throte,',),' throat,'),((' throte.',),' throat.'),((' throte?',),' throat?'),((' throte:',),' throat:'),
                    (('Trone ',),'Throne '),((' trone ',),' throne '),((' trone,',),' throne,'),((' trone.',),' throne.'),((' trone?',),' throne?'),
                        (('thronge ','thrunge ','througe '),'throng '),
                    ((' throughly',),' thoroughly'), (('thorowout',),'throughout'), (('Thorowe ','Thorow '),'Through '),(('thorouy ','thorowe ','thorow ','thorou ','thoruy ','thorw '),'through '),(('thorowe,','thorow,'),'through,'),(('thorow.',),'through.'),(('thorowe:',),'through:'),((' thorou;',),' through;'),
                    (('throwen','throwne'),'thrown'),
                (('thrusteth','throusteth'),'thrusteth/thrusts'),((' thristynge',),' thrusting'),(('thruste ',),'thrust '),
            ((' thumbe',),' thumb'),
                (('thundred',),'thundered'),(('thundringes','thundrings','thondringes','thundris'),'thunderings'),(('thundryng',),'thundering'),(('thounder','thonder','thuder'),'thunder'),
            # (('>thyself<',),'>thyself/yourself<'),
            # (('thyself',),'thyself/yourself'),# (('thyself,',),'thyself/yourself,'),(('thyself.',),'thyself/yourself.'),(('thyself:',),'thyself/yourself:'),(('thyself;',),'thyself/yourself;'),
        (('Tydinges',),'Tidings'),((' tidings',' tidinges',' tydynges',' tidynges',' tydinges',' tydings'),' tidings/news'), ((' tyde',),' tide'),
            ((' tyed ',),' tied '),((' tyed,',),' tied,'),((' tyed:',),' tied:'),
            (('Tikuah',),'Tikvah'),
            ((' tiel ',),' tile '), ((' tyll ',' tyl ',' til '),' till '),
            ((' tymber',' tymbre'),' timber'), ((' timbrelles',' tymbrels'),' timbrels'),((' timbrell ',),' timbrel '),((' timbrell:',),' timbrel:'), ((' tyme',),' time'),
            ((' tynne ',),' tin '),((' tinne,',' tynne,',' tyn,'),' tin,'),
            ((' tippe ',),' tip '),
            ((' tithis',),' tithes'),((' tythe',),' tithe'), ((' titil ',),' title '),
        (('togedder','togidir','togidere','togydere','togidre','togider'),'together'),
            ((' tokens',' tokenes'),' tokens/signs'),((' token',' tokene',' tokyn',' tokne'),' token/sign'),
            ((' toolde ',' tolden ',' tolde ',' telden ',' telde ',' teld '),' told '),((' tolde,',),' told,'),((' tolde.',),' told.'),((' tolde:',),' told:'), ((' tolle,',),' toll,'),
            ((' tombes',),' tombs'),((' toumbe',' tombe'),' tomb'),
            ((' tongis',),' tongs'),
                ((' tungis',' tunges',' tonges',' toges',' tuges'),' tongues'),((' tounge',),' tongue'),((' tonge ',' tunge ',' toge '),' tongue '),((' tonge,',' tunge,',' tuge,',' toge,'),' tongue,'),((' tonge.',' tunge.',' toge.'),' tongue.'),((' tonge?',),' tongue?'),((' tonge:',),' tongue:'),((' tunge;',),' tongue;'),
            ((' tookest',' tokest',' tokist'),' tookest/took'),((' tokun ',' tooke ',' toke '),' took '), ((' toole ',),' tool '),
            ((' toppes',),' tops'),((' toppe ',),' top '),
            ((' turmentiden',' turmentid'),' tormented'),((' tormenteth',' turmentith'),' tormenteth/torments'),((' turmente ',),' torment '),((' turment',),' torment'),
                ((' torne ',),' torn '),((' torne,',),' torn,'),
            ((' tottringe',),' tottering'),
            ((' touchiden',' towchyde',' touchide',),' touched'),((' toucheth',' touchith'),' toucheth/touches'),((' touchinge',),' touching'), (('Touche ',),'Touch '),((' touche ',),' touch '),((' touche;',),' touch;'),
            ((' towardes',),' towards'),((' towarde ',),' toward '),
                ((' towres',' touris'),' towers'),((' towre ',' toure '),' tower '),((' towre,',' toure,'),' tower,'),
                ((' towne',' toune',' toun'),' town'), # ((' townes',' tounes'),' towns'),
        (('tradicioun','tradicion'),'tradition'),((' traditio ',),' tradition '),
                ((' traffique ',' traffick '),' traffic '),
                ((' traine,',),' train,'), (('traytoure','traytour'),'traitor'),
                (('tranquillitie',),'tranquillity'),
                    (('ttasfigured','transfigurid'),'transfigured'),
                        (('transgressour',),'transgressor'),(('transgresse ',),'transgress '),(('transgresse,','trasgresse,'),'transgress,'),(('transgresse.',),'transgress.'),(('transgresse:',),'transgress:'),
                        (('translatidist','translatide','translatid'),'translated'),(('translacioun',),'translation'),
                        (('transmygracioun',),'transmigration'),
                ((' traueilide',' trauelede',' trauailed',' traueiled',' trauayled'),' travailed'),(('travailest','trauelist','traueilist'),'travailest/travail'),(('travaileth','traueileth','trauaileth','traueilith','trauelleth','trauayleth','traualeth'),'travaileth/travails'),(('trauelinge','trauelynge','trauailing','traueiling'),'travailing'), ((' trauelis',),' travails'),(('trauayle','trauaile','traueile','trauell'),'travail'),
                    ((' trauelide',' trauelid'),' travelled'),((' travelleth',' traueleth',' traveleth'),' travelleth/travels'), ((' trauele ',),' travel '),((' trauel',),' travel'),
            (('Treade ',),'Tread '),((' treade ',),' tread '), ((' tresoun',),' treason'),
                    (('tresouris','treseries'),'treasuries'),(('treasurie ','tresorie '),'treasury '),((' treasurie,',),' treasury,'),((' treasurie.',' tresorie.'),' treasury.'),((' treasurie:',),' treasury:'), ((' tresoure',' tresour'),' treasure'),
                ((' treblid',),' trebled'),
                ((' tre ',),' tree '),((' tre,',),' tree,'),((' tre.',),' tree.'),((' tre:',),' tree:'),((' tre;',),' tree;'),
                ((' trelies',),' trellis'),
                (('trembliden','tremblide'),'trembled'),(('trembleth','trebleth'),'trembleth/trembles'),(('trymblinge','tremblinge','tremblynge','tremblyng'),'trembling'),
                ((' trespacers',),' trespassers'),(('trespasside','trespassid','trespaced'),'trespassed'),(('trespassyng','trespassiden','trespasseden'),'trespassing'), (('trespassis','treaspases','trespaces','trespases'),'trespasses'),
                    (('trespasse ','trespace ','trespas '),'trespass '),(('trespasse,','trespas,'),'trespass,'),(('trespasse.','trespace.','trespas.'),'trespass.'),(('trespas?',),'trespass?'),(('trespas;',),'trespass;'),
            (('trybe ',),'tribe '),(('trybes',),'tribes'),
                    (('tribulacioun','tribulacion'),'tribulation'), (('tributary.','tributarie.',),'tributary/paying_tribute.'),(('tributary?','tributarie?'),'tributary/paying_tribute?'),(('tributary!',),'tributary/paying_tribute!'),(('trybute',),'tribute'),
                ((' tryed',),' tried'),
                ((' trymmed',),' trimmed'),
                (('tryumphe ','triumphe ','triuphe '),'triumph '),
            ((' treden ',' trode ',' trood '),' trod '),((' troden',),' trodden'),
                ((' troupe',),' troop'), #((' troupes',),' troops'),((' troupe ',),' troop '),((' troupe,',),' troop,'),((' troupe:',),' troop:'),((' troupe?',),' troop?'),
                (('troblere',),'trouble-maker'), ((' troublide',' troublid',' troblid'),' troubled'),((' troublinge',' troblen'),' troubling'),((' truble ',),' trouble '),
                (('trowell ',),'trowel '),
            (('Treuli','Truely','Sotheli'),'Truly'),(('truely','treuli','sotheli'),'truly'),
                (('trumpetter',),'trumpeter'),(('trumpettes','tropettes','trumpis','trompes'),'trumpets'),((' trompette ',' trompet ',' tropet ',' trumpe '),' trumpet '),((' trompet,',' trumpe,'),' trumpet,'),((' trumpe.',' tropet.'),' trumpet.'),
                (('sothfast',),'truthful'), ((' truethes',' truthes'),' truth’s'), (('Treuthe ','Trueth ','Treuth '),'Truth '),((' trewthe',' trueth',' treuthe',' treuth',' truthe'),' truth'), ((' trewe',),' true'),
                ((' trustie ',),' trusty '), ((' tristydist',),' trusted'),((' trusteth',' tristith'),' trusteth/trusts'), (('Triste',),'Trust'),((' tristen ',' truste ',' triste '),' trust '),((' truste:',),' trust:'),
            ((' trieth',' tryeth'),' trieth/tries'), (('Trye ',),'Try '),((' trye ',' trie '),' try '),
        ((' toordis',),' turds'), ((' turnedest',' turneden',' turnede',' tourned'),' turned'),(('Turne ','Tvrne '),'Turn '),((' tourne ',' turne '),' turn '),((' turne,',),' turn,'),((' turne.',),' turn.'),((' turne:',),' turn:'),
        (('Twei ',),'Twain/Two_or_both '), ((' twain ',' twei ',' tweyne ',' tweyn ',' twey ',' twaine ',' twayne '),' twain/two_or_both '),(('twain,','twaine,','twayne,','tweyne,'),'twain/two_or_both,'),
            ((' tweluethe',' twelfthe',' twolueth'),' twelfth'),((' twelft ',),' twelfth '), (('Twelue',),'Twelve'),(('twolue','twelue'),'twelve'), (('twentithe','twentith'),'twentieth'), (('Twentie ','Twetye '),'Twenty '),(('twentie ','twenti ','twentye '),'twenty '),(('twentie.','twentye.'),'twenty.'),(('twentie:',),'twenty:'),(('twenti;',),'twenty;'),
            ((' twyse',' twise',' twies'),' twice'),
                (('twincklinge',),'twinkling'), (('twynnes','twinnes','twyns'),'twins'),

        (('Tyrany',),'Tyranny'),((' tiranny',),' tyranny'), (('Tyraunt',),'Tyrant/Dictator'),((' tyrants',' tyrauntes',' tirauntes'),' tyrants/dictators'),((' tyrant ',' tyraunte ',' tiraunt '),' tyrant/dictator '),
    (('vnauenged',),'unavenged'), (('vnaduisedly',),'unadvisedly'), (('vnawarres','vnwares'),'unawares'),
        (('vnbeleefe','vnbileue','vnbelefe','vnbeleue','vnbeliefe'),'unbelief'), (('vnbeleuing','vnbeleuynge'),'unbelieving'),
            ((' vnbynde',),' unbind/untie'),
            ((' vnborne',),' unborn'), ((' vnboundun',),' unbound'),
        (('vncerteyn',),'uncertain'),
            (('vnchastite',),'unchastity'),
            (('vncircumcized','vncircumcidid'),'uncircumcised'),
                    (('vnclennesses',),'uncleannesses'),
                    (('vncleannesse ','vnclennesse ','vncleannes ','vnclennes '),'uncleanness '),(('vncleannes,','vnclennesse,','vnclennes,'),'uncleanness,'),(('vncleannesse.','vnclennesse.'),'uncleanness.'),
                    (('vncleane','vncleene','uncleene','vnclene'),'unclean'),
                (('Uncouer','Vncouer'),'Uncover'),(('vncover','vncouer'),'uncover'),
                (('vnkunnynge','vnkunnyng'),'uncunning/uneducated'),
            (('vndefyled',),'undefiled'),
                    (('vndurgoynge',),'undergoing'),
                    (('understandest','vnderstandest'),'understandest/understand'),(('understandeth','vnderstandeth','vndirstondith','vndurstondith','vnderstondeth'),'understandeth/understands'),(('vnderstondynge','vndirstondynge','vnderstondyng','vndurstondyng','vnderstanding','vnderstading'),'understanding'), (('Vndurstonde',),'Understand'),((' vnderstande',' vnderstonde',' vndirstonde',' vnderstand',' vnderstond'),' understand'),
                        (('Vnderstonde',),'Understood'),(('vndurstonden','vnderstonde','vndurstonde','vnderstoode','vndurstoden','vnderstode','vndirstood'),'understood'),
                    (('vndertoke',),'undertook'), (('Vnder',),'Under'),((' vnder',' vndir',' vndur'),' under'),
                ((' vndon.',),' undone.'),((' vndoe ',),' undo '),
            (('vnfaithfully',),'unfaithfully'),(('vnfeithfulnesse','vnfeithfulnes'),'unfaithfulness'),(('vnfaithfull ','vnfeithful ','unfaithfull '),'unfaithful '), (('vnfensed',),'unfenced'),
            (('vngodlynes',),'ungodliness'),(('vngodlye',),'ungodly'),
                (('vngraciousnesse','vngratiousnesse','vngraciousnes'),'ungraciousness'),
            ((' vnhooli',),' unholy'),
            (('Vnicorne',),'Vnicorn'),((' vnicorne',),' unicorn'), ((' vnitie',),' unity'),
            ((' vniustli',),' unjustly'),((' vniust',),' unjust'),
            (('VNKNOWEN',),'UNKNOWN'),
            ((' vnlerned',),' unlearned'),(('vnleauened','vnleuended','vnleuened'),'unleavened'), (('Unlesse ',),'Unless '),((' vnlesse ',),' unless '), ((' vnloose',),' unloose'),
            (('vnmouable',),'unmovable'),
            (('vnquietnesse',),'unquietness'),
            (('vnresonable',),'unreasonable'),
                (('vnrighteousnesse ','vnrightuousnesse '),'unrighteousness '),(('vnrigthuousnesse.','vnrightuousnes.'),'unrighteousness.'), (('vnryghteous','vnrightuous'),'unrighteous'),
                ((' vnrulye',' vnruly'),' unruly'),
            ((' unsadlide',' vnsadled'),' unsaddled'),
                ((' vnsauerie',' vnsauoury',' vnsauery',' vnsavery',' unsauery',' unsavery'),' unsavoury'),
            ((' vntieden',),' untied'),
                    ((' vntilid',),' untilled'), (('Untyll ','Vntill ','Vntil ','Untill '),'Until '),(('vntill','vntyll'),'until'),
                    (('vntymely',),'untimely'),
                (('Vnto ',),'Unto '),((' vnto',),' unto'),(('(vnto',),'(unto'),#(('>vnto',),'>unto'),
                ((' vntrueth',),' untruth'),
                ((' vntiynge',),' untying'),
            ((' vnwyse',' vnwijs'),' unwise'),
        ((' vp ',),' up '),((' vp,',),' up,'),((' vp.',),' up.'),
            ((' upheld',' vpholded',),' upheld/supported'),((' uphold ',' vpholde ',' vphold '),' uphold/support '),
            (('Vpon ','Vpo '),'Upon '),((' vppon ',' vpon ',' upo ',' vpo ',' apon '),' upon '),((' upo:',),' upon:'),
            (('vprightnesse ','vprightnes ','vprighteous '),'uprightness '),(('vprightnes.',),'uprightness.'), ((' vprightlye',),' uprightly'), ((' vpryght',' vpriyt'),' upright'),
                ((' vproare',' vproure',' vprore'),' uproar'),
            (('vpsodoun',),'upsidedown'),
            ((' vpwarde',' vpward'),' upward'),
        ((' vrged',),' urged'), ((' vrgent',),' urgent'),
        (('Vse ',),'Use '),((' vsid',),' used'),((' vsis',),' uses'),
            (('Vzziah',),'Uzziah'),
            ((' vsuris',),' usurers'),((' vsurie',' vsury'),' usury'),
        (('Outirli',),'Utterly'),((' vtter',' vter',' vtte'),' utter'), # includes utterly and uttermost
            ((' vtmost',),' utmost'),
            ((' vnwaisschen',' vnwasschen',' vnwasshen',' vnwesshen',' vnweshen',' vnwashen',' unwashen'),' unwashed'),
            ((' vn',),' un'), # Special case for all remaining un- words
            ((' VP',),' UP'),((' vp',),' up'), # Special case for all remaining up- words (ALL CAPS in Dan 5:25)
            ((' vs',),' us'), # 'us' plus special case for all remaining us- words
    ((' vagabounde',' vagabunde'),' vagabond'),
            ((' veynli',),' vainly'), (('Vayne ','Uayne '),'Vain '),((' vaine',' vayne',' veyne',' veyn'),' vain'),
            ((' valiaunt',' valeaunt',' valeaut',' viliant'),' valiant'), ((' valleis',' valleyes'),' valleys'),((' valey',' valei'),' valley'),
                ((' valuest',),' valuest/value'),
            (('vanisshed','vanysshed'),'vanished'),((' vanishe ',),' vanish '),
                (('vanytees',),'vanities'), (('Uanitie ','Vanitie '),'Vanity '),((' vanitie ',' vanytie ',' vanytee ',' vanyte ',' vanite '),' vanity '),((' vanitie,',' vanite,',' vanyte,'),' vanity,'),(('vanitie.','vanite.','vanyte.'),'vanity.'),(('vanitie?','vanyte?'),'vanity?'),(('vanitie:','vanite:'),'vanity:'),(('vanytee;','vanyte;'),'vanity;'),
            ((' vapor',),' vapour'),((' vapoure ',),' vapour '),
            ((' variaunce',),' variance'),
        (('Uaile',),'Veil'),((' vayle',' vaile',' vail'),' veil'),
            ((' vengeaunce',' veniaunce',' avengaunce'),' vengeance'), ((' venym',),' venom'),
            (('Uery ',),'Very '),
            ((' vesseli',' vessell',),' vessel'),
            ((' vestrie',' vestrye'),' vestry'),
            ((' vexation',' vexacion',' vexacio'),' vexation/frustration'), ((' vexe ',),' vex '),
        ((' vyce ',),' vice '), ((' victorie ',),' victory '),((' victorie,',' victorye,',),' victory,'),
                ((' victuall',),' victual'),
            ((' vyllagies',' vyllages',' villagis'),' villages'), ((' vileny',),' villainy'),
            ((' vynes',),' vines'), (('Uine',),'Vine'),((' vyne ',' vyn '),' vine '),((' vyne,',),' vine,'),((' vyne.',),' vine.'),((' vyne:',),' vine:'),((' vyne;',),' vine;'),
                ((' vineger',),' vinegar'),
                ((' vyneris',),' vineries/vineyards'),(('vyneyerdis','vinyardes','vynyaydes'),'vineyards'),(('vynyearde','vineyarde','vyneyarde','vynyarde','vyniarde','vinyarde','vynyerd','vyner','vnieyarde'),'vineyard'),
            ((' vyndage',),' vintage'),
            ((' violece',),' violence'),
            (('virginitie','virginiti',),'virginity'),(('Uirgin','Virgine'),'Virgin'),((' virgine',' virgyn',' vyrgin',' vergyn'),' virgin'),
                ((' vertu ',),' virtue '),((' vertu,',),' virtue,'),((' vertu;',),' virtue;'),((' vertue',),' virtue'),
            ((' visios',),' visions'), (('Uision ',),'Vision '),((' visioun',),' vision'),
                (('visitacioun','visitacion'),'visitation'), (('vysited',),'visited'),(('visiteth','visitith'),'visiteth/visits'),(('visitest','visitist'),'visitest/visit'),(('visityng',),'visiting'),((' visite ',),' visit '),((' viset',' vyset'),' visit'),((' visite,',),' visit,'),
            ((' vittayles',' vitailes',' vytayles'),' vitals/essentials'),
        ((' voyce',' vois',' voys'),' voice'), ((' voyde',' voyd',' voide'),' void'),
            ((' vowest',),' vowest/vow'),((' vowes ',' vowis '),' vows '),((' vowes,',),' vows,'), (('Vowe ',),'Vow '),((' vowe ',),' vow '),((' vowe,',),' vow,'),((' vowe:',),' vow:'),
    ((' wagginge',),' wagging'),((' wagge ',),' wag '),
            ((' wayled',),' wailed'), (('Weilyng',),'Wailing'),(('Weile ',),'Wail '), ((' weilynge',' weilyngi',' weilyng',' weiling'),' wailing'),((' waile ',' weile '),' wail '),((' weile,',),' wail,'),
                ((' wayted',),' waited'), ((' waiteth',' wayteth'),' waiteth/waits'), ((' waytinge',),' waiting'), (('Wayte ',),'Wait '),((' wayte ',' waite ',' wate '),' wait '),((' waite,',' wayte,'),' wait,'),((' waite:',),' wait:'),
            ((' waketh',' wakith'),' waketh/wakes'), ((' wakyngis',),' wakings'),
            (('walkynge','walkinge'),'walking'),((' walkide',' walkid'),' walked'),(('Walke ',),'Walk '),((' walke ',),' walk '),((' walke,',),' walk,'),((' walke:',),' walk:'),
                ((' walewide',),' wallowed'),((' walowinge',' walowing'),' wallowing'),
                ((' wallid',),' walled'),((' walles',' wallis',' wals'),' walls'),
                ((' wal ',),' wall '),((' wal,',),' wall,'),((' wal.',),' wall.'),((' wal;',),' wall;'),
             ((' wandride',' wandred'),' wandered'),((' wandrynge',),' wandering'), ((' wandre ',),' wander '),((' wandre,',),' wander,'),
                (('wantonnes,',),'wantonness,'), ((' wantynge',),' wanting'),((' wante ',),' want '),
             ((' warres',),' wars'),((' warre ',),' war '),((' warre,',),' war,'),((' warre.',),' war.'),((' warre?',),' war?'),((' warre:',),' war:'),((' warre;',),' war;'),
                ((' wardes',),' wards'),((' warde ',),' ward '),((' warde.',),' ward.'),
                ((' warely',' warli',),' warily'),
                ((' warmede',),' warmed'), ((' warme ',),' warm '),((' warme,',),' warm,'),((' warme.',),' warm.'),((' warme:',),' warm:'),
                ((' warnynge',),' warning'), ((' warne ',),' warn '),
                ((' warryour',' werriour',' warrier'),' warrior'),
             ((' wass ',),' was '),
                ((' waischiden',' waisschide',' waischide',' waischid',' wasshed',' wesshed',' washen',' washt'),' washed'),((' wasschyngi',' waisschen',' wasshynge',' wesshinge',' waischyng',' waisschun',' washinge',' wasshinge',' waischun',' wasshing',' wasshyng'),' washing'),
                    (('Washe ',),'Wash '),((' waische ',' wesshe ',' wasshe ',' washe '),' wash '),((' wasshe,',),' wash,'),((' wasshe.',),' wash.'),((' wassche;',),' wash;'),
                ((' wastide',' waysted',' wastyd',' waastid',' wastid'),' wasted'),((' waistinge',),' wasting'),((' waaste',' waiste'),' waste'), (('wastenesse ','wasteness '),'wasteness/disaster '),
            (('Watche',),'Watch'),((' watche ',),' watch '),((' watche.',),' watch.'),((' watche:',),' watch:'),
                ((' waterpooles',),' water-pools'), ((' watred',),' watered'), (('Watris',),'Waters'),((' watris',),' waters'),((' watir',' watre'),' water'),
            ((' waue',' wawi',' wawe'),' wave'), # Those were all plural -- might overreach now ???
            ((' waxe ',),' wax '),((' waxe,',),' wax,'),((' waxe.',),' wax.'),((' waxe:',),' wax:'),
            (('waiwardli',),'waywardly'),(('weiwardnesse',),'waywardness'),((' weiward',' waiward'),' wayward'),
                ((' waies',' wayes',' weies'),' ways'),((' waye ',' waie ',' weie ',' weye '),' way '),((' waye,',' weie,',' waie,',' weye,'),' way,'),((' waye.',' weie.',' weye.',' waie.'),' way.'),((' waye?',' waie?',' weie?'),' way?'),((' waye:',' weie:',' weye:'),' way:'),((' weie;',),' way;'),
        (('Wee ',),'We '),((' wee ',),' we '),((' wee?',),' we?'),((' wee:',),' we:'),
            ((' weake ',),' weak '),((' weake,',),' weak,'),((' weake.',),' weak.'),((' weake:',),' weak:'),
                ((' wealthyest',' welthiest',' welthyest'),' wealthiest'), ((' welthynesse',' welthinesse'),' wealthiness'), ((' welthy',),' wealthy'),
                ((' wayned',' wained',' weened',' wenyde'),' weaned'),
                ((' weapen',' wapen'),' weapon'),
                ((' weare ',' weere ',' wayre '),' wear '), ((' weeried',' weryed',' weried'),' wearied'),((' wearieth',' weerieth'),' wearieth/wearies'),((' wearie ',' weerie ',' weery ',' wery '),' weary '),((' wearie,',),' weary,'),((' wearie:',' weery:'),' weary:'),((' wearie?',),' weary?'), (('weerinesse ','weerynesse ','weerynes ','wearines '),'weariness '),(('weerinesse,',),'weariness,'),
                ((' weauer',' weeuer'),' weaver'),
            ((' webbis',),' webs'),((' webbe ',),' web '),
            ((' weddid',),' wedded'),((' weddeth',' weddith'),' weddeth/weds'), ((' weddyngi',' weddyngy',),' wedding'), ((' wedlocke',),' wedlock'),
            ((' wedes',),' weeds'),
            ((' weightie ',),' weighty '), ((' weiytis',' weightes',' waightes',' wayghtes'),' weights'), ((' waight',' wayght',' weiyte'),' weight'), ((' weyed',),' weighed'),((' waigh',' waygh'),' weigh'),
            ((' woukis',' weekes',' wekes'),' weeks'),((' weeke',' weke'),' week'),
                ((' weepeth',' wepeth',' wepith',),' weepeth/weeps'),((' weepyng',' wepyng',' weepinge',' wepinge',' weping',' wepige',' wepingi',' wepen'),' weeping'),((' wepten',' weapte',' wepte',),' wept'),((' weepe ',' wepe '),' weep '),((' weepe,',' wepe,'),' weep,'),((' wepe.',),' weep.'),((' weepe?',' wepe?'),' weep?'),((' weepe:',' wepe:'),' weep:'),((' wepe;',),' weep;'),
            ((' welde ',),' weld '),((' welde,',),' weld,'),
                (('weldoynge',),'well-doing'), ((' welles',' wellis'),' wells'), (('Wel ',),'Well '),(('Wel,',),'Well,'),((' welle ',' wel '),' well '),((' wel,',),' well,'),((' wel.',),' well.'),((' wel:',),' well:'),((' wel;',),' well;'),
            ((' wenten ',' wente ',' wete ',' yeden ',' yede '),' went '),((' wente,',' wete,',' yede,'),' went,'),((' wente.',),' went.'),
            ((' werest',),' werest/were'), ((' weren ',' werre ',' wert '),' were '),((' weren.',' wert.'),' were.'),((' weren;',),' were;'),
            (('westwarde',),'westward'), ((' weste',),' west'),
            ((' wetheris',),' wethers'),((' wethir',),' wether'), ((' wette ',),' wet '),
        (('whalfishes',),'whales'),
                ((' wha ',' wote ',' wot '),' what '), ((' whateuer',),' whatever'), (('Whatsoeuer',),'Whatsoever'),(('whatsoeuer',),'whatsoever'),
            ((' wheete',' wheate',' whete'),' wheat'),
                ((' wheeles',),' wheels'),((' wheele',' whele'),' wheel'),#((' wheele,',),' wheel,'),((' wheele:',),' wheel:'),
                ((' whelps',' whelppes',' whelpes',' whelpis',' welpes'),' whelps/pups_or_cubs'),((' whelp ',' whelpe '),' whelp/pup_or_cub '),
                (('Whensoeuer ',),'Whenever '), (('Whanne ','Whane ','Whan ','Whe '),'When '),((' whanne ',' whane ',' whan ',' whe '),' when '),
                (('Wher ',),'Where '),(('Wheras ',),'Whereas '),((' wheras ',),' whereas '), ((' wherby',' wherbi'),' whereby'), (('Wherfore','Wherfor'),'Wherefore'),((' wherfore ',' wherfor '),' wherefore '), ((' wherynne ',' wherin '),' wherein '), (('Wherof ',),'Whereof '),(('wherof ',),'whereof '),
                    (('Whidur ever','Wheresoever','Where so ever','Wheresoeuer','Whersoeuer'),'Wherever'),(('wheresoever','wheresoeuer','whersoeuer','whersoever'),'wherever'), (('whervnto',),'whereunto'), (('wherevpon','whervpon','wherupon','wher upon','wheron'),'whereupon'), (('wherwith',),'wherewith'),
                (('Whethir',),'Whether'),((' whethir',' whidir'),' whether'),
            (('Whiche ','Whyche '),'Which '),((' whiche ',' whyche ',' whis ',' wich '),' which '),((' whiche,',),' which,'),(('(whiche ',),'(which '),
                ((' whilst',' whilest',' whylest',' whiles'),' whilst/while'), (('Whyle ','Whyll '),'While '),((' whill ',' whyll ',' whyle '),' while '),((' whyle,',),' while,'),
                ((' whippes',),' whips'),
                (('whirle-winde','whirlewynde','whirlewynd','whirlewinde','whirlewind','whirlwynd'),'whirlwind'),
                ((' whisperinge',),' whispering'), ((' whystle',),' whistle'),
                (('whithersoever','whithersoeuer','whithersouer','withersoeuer','whethersoeuer'),'whithersoever/wherever'), (('Whither ','Whyther ','Whidir '),'Whither/Where '),(('whither ','whyther ','whidur '),'whither/where '),
                    ((' whitere',),' whiter'),(('whyte','whyt','whijt'),'white'),
            ((' wholy',),' wholly'), ((' holsome',),' wholesome'), (('Hoole ',),'Whole '),((' whoale',' hoole',' hool'),' whole'),
                (('Whome',),'Whom'),((' whome',' whō'),' whom'), (('Whomsoeuer',),'Whomsoever'),(('whomsoeuer',),'whomsoever'),
                (('whoredoms','whoredomes','whordomes'),'whoredoms/prostitutions'), (('Whoredom ',),'Whoredom/Prostitution '),(('Whoredom,','Whoredome,''Whordome,'),'Whoredom/Prostitution,'),(('whoredom ','whoredome ','whordome '),'whoredom/prostitution '),(('whoredom,','whoredome,','whordome,'),'whoredom/prostitution,'),(('whoredome.','whordome.'),'whoredom/prostitution.'),(('whoredom:','whoredome:','whordome:'),'whoredom/prostitution:'), (('whoringe','whoryng'),'whoring'), (('hooris',),'whores'),(('whoore','hoore',),'whore'),
                (('Whosoeuer',),'Whosoever'),(('whosoeuer',),'whosoever'), ((' whos ',),' whose '),
            (('Whi ',),'Why '),((' whi ',),' why '),
        ((' wickidli',),' wickedly'), (('wickidnessis','wickednessis','wyckidnessis'),'wickednesses'), (('Wickednesse ','Wickednes '),'Wickedness '),(('wickidnesse ','wickednesse ','wyckednes ','wickednes '),'wickedness '),(('wickidnesse,','wickednesse,','wickednes,'),'wickedness,'),(('wickidnesse.','wickednesse.','wickednes.'),'wickedness.'),(('wickidnesse?','wickednes?'),'wickedness?'),(('wickednesse:','wickednes:'),'wickedness:'),(('wickidnesse;','wickednesse;','wickednes;'),'wickedness;'), ((' wickid',' wickyd'),' wicked'),
            ((' wyder',),' wider'),((' wyde ',),' wide '),((' wyde,',),' wide,'),((' wyde:',),' wide:'),
                (('widewis','widdowes','wyddowes','wydowes','widowes','wedowes'),'widows'),(('widewe ','wyddowe ','wydowe ','widdowe ','widowe '),'widow '),(('widdowe,','wyddowe,','widewe,','widowe,','wedowe,'),'widow,'),(('wyddowe.','wydowe.','widowe.','widewe.'),'widow.'),(('widowe:',),'widow:'),(('widewe;',),'widow;'),
                    (('wildirnesses',),'wildernesses'),(('wyldernesse','wildirnesse','wyldernes'),'wilderness'), (('wildernesse ','wildernes '),'wilderness '),(('wildernes,',),'wilderness,'),(('wildernesse?','wildernes?'),'wilderness?'),(('wildernes:',),'wilderness:'),
            ((' wyfe',' wijf',' wiyf'),' wife'),
            (('Wielde ',),'Wild '),((' wielde ',' wilde ',' wylde ',' wyelde '),' wild '), (('wildernes.',),'wilderness.'),
                (('wylfulnesse',),'wilfulness'), ((' wilfuli',),' wilfully'),((' wylfull ',),' wilful '),
                ((' willis',),' wills'), (('Wyll ',),'Will '),((' wyll ',' wyl ',' wille ',' wil ',' wole '),' will '),((' wille,',' wyll,',' wil,',' wole,'),' will,'),((' wille.',' wyll.'),' will.'),((' wyll:',' wil:'),' will:'), (('Wilt ','Wylt '),'Wilt/Will '),((' wilt ',' wylt '),' wilt/will '),((' wilt,',' wylt,'),' wilt/will,'),
                    (('wyllingly','wyllyngly'),'willingly'),((' wyllynge',' wyllinge',' wyllyng'),' willing'),
                    ((' wyllowe',' willowe'),' willow'),
            ((' winne ',' wynne '),' win '),((' wynne,',),' win,'),
                ((' wyndis',' wyndes',' windes'),' winds'),((' windie',),' windy'), ((' wynde ',' wynd ',' winde '),' wind '),((' winde,',' wynde,',' wynd,'),' wind,'),((' winde.',' wynde.'),' wind.'),((' winde?',' wynde?'),' wind?'),((' winde:',' wynde:'),' wind:'),((' wynde;',' wynd;'),' wind;'),
                    ((' windowe',' wyndowe',' wyndow'),' window'), # ((' windowes',' wyndowes',' wyndows'),' windows'),
                ((' wynes',),' wines'),((' wyne ',' wiyn ',' wyn '),' wine '),((' wyne,',' wiyn,',' wijn,',' wyn,'),' wine,'),((' wyne.',' wyn.'),' wine.'),((' wyn?',),' wine?'),((' wyne:',),' wine:'),((' wyn;',),' wine;'),
                ((' wyngis',' wengis',' wynges',' winges'),' wings'),
                ((' wyncke ',' winke '),' wink '),((' wynck',' wynk'),' wink'),
                ((' winneth',' wynneth'),' winneth/wins'),((' wynnynge',),' winning'),
                (('Wynter',),'Winter'),((' wyntir',' wynter'),' winter'),
            ((' wipte',' wyped'),' wiped'),((' wype',),' wipe'),
            ((' wiseli',),' wisely'),((' wyse',' wijs'),' wise'), #((' wyse,',),' wise,'),
                (('Wisedome','Wy?dome'),'Wisdom'),(('wyssdome','wysedome','wysdome','wisedome','wisedom','wisdome','wysdom','wy?dome','wysdo'),'wisdom'),
                ((' wysshed',' wisshed'),' wished'), ((' wisheth',' wyssheth',' wysheth'),' wisheth/wishes'), (('Wishe ','Wysh '),'Wish '),((' wyshe ',' wishe '),' wish '),((' wysh',),' wish'),
            ((' wychcraft',),' witchcraft'),
                (('withdrawne','withdrowen','withdrawen'),'withdrawn'), (('Withdrawe ',),'Withdraw '),((' withdrawe ',),' withdraw '),
                    (('widdred','wythred','wythered','wyddred'),'withered'),(('withereth','wythereth'),'withereth/withers'), ((' wyther',),' wither'),
                    ((' withynne',),' within'), ((' wyth ',' wi ',' wt '),' with '),
                    (('withholden','witholdun','withhelde','withelde'),'withheld'),(('withholde ','witholde '),'withhold '),
                        (('withouten ','withoute '),'without '), (('witnesside',),'witnessed'),(('witnessyngi','witnessyng'),'witnessing'),(('witnessis','wytnesses'),'witnesses'),((' wytnesse ',' witnesse ',' witnes ',' wytnes '),' witness '),((' wytnesse,',' witnesse,',' witnes,'),' witness,'),((' wytnesse.',),' witness.'),((' witnes?',),' witness?'),((' wytnesse:',' wytnes:'),' witness:'),
                ((' wittes',' wittis'),' wits'), ((' witti',),' witty'),
            ((' wyues',' wiues'),' wives'),
        (('Woo ','Wo '),'Woe '),(('Wo.',),'Woe.'),((' wo ',),' woe '),((' wo.',),' woe.'),((' wo!',),' woe!'),
            ((' woolues',' wolues'),' wolves'),((' wolfe',),' wolf'),
            ((' womman',),' woman'),((' woma ',),' woman '), ((' wombe',' wombi',' wobe'),' womb'),
                ((' wymmen',' wemen'),' women'),((' weme ',' wome '),' women '),((' wome,',),' women,'),
            ((' wonne ',),' won '),((' wonne,',),' won,'),((' wonne.',),' won.'),
                (('wondriden','wondride','wondred'),'wondered'),((' wondringe',' wondrynge',' wondryng',' wondring'),' wondering'),
                    (('wondurfuli','wondirfuli'),'wonderfully'),(('wonderfull ','wondirful ','wondurful ','woderfull '),'wonderful '),(('wonderfull,','wondirful,'),'wonderful,'),(('wonderfull.',),'wonderful.'),(('wonderfull:',),'wonderful:'), ((' woonders',' wondris',' woders'),' wonders'),((' wondre',),' wonder'),
                    (('Wonderous',),'Wondrous'),((' wonderous',' woderous'),' wondrous'),
            ((' wodis',' woddes'),' woods'),((' wode ',' wodd ',' wod '),' wood '),((' wodde,',' wode,',' wodd,'),' wood,'),((' wod.',),' wood.'),((' wodd?',),' wood?'),
                ((' wollun',' wollen',' woolen',' wolen',),' woollen'), ((' wollis',),' wools'),((' wooll ',' woll '),' wool '),((' wooll,',' wolle,',' woll,'),' wool,'),((' wooll.',' woll.'),' wool.'),((' wooll:',' woll:'),' wool:'),
            ((' wordis',' wordys',' woordes',' wordes'),' words'),((' woorde',' worde',),' word'),
                ((' woorker',),' worker'), ((' workemen',),' workmen'),((' workeman',),' workman'), ((' woorkes',' workes',' workis',' werkis'),' works'),
                    ((' worketh',' worchith'),' worketh/works'),((' worching',' worchen',' workyng'),' working'),((' worche ',' woorke ',' worke ',' werke ',' werk '),' work '),((' woorke,',' worche,',' worke,',' werk,'),' work,'),((' worche.',' worke.',' werk.'),' work.'),((' worke?',' werk?'),' work?'),((' worke:',),' work:'),
                ((' worldis',),' worlds'),((' worlde',),' world'),
                ((' wormes ',),' worms '),((' worme ',),' worm '),
                ((' worne ',),' worn '),
                (('worschiper',),'worshipper'), (('worschipfuli',),'worshipfully'),
                        (('worschipiden','worschipide','worschipid','worshypped','worshiped'),'worshipped'), (('worshippeth','worschipith'),'worshippeth/worships'), (('Worschipe',),'Worship'),(('worschipen ','worschipe ','worshippe ','worshipe '),'worship '),(('worshipe,',),'worship,'),((' worschip',' worshyp'),' worship'),
                    ((' worsse',),' worse'),((' wors,',),' worse,'),((' worste ',),' worst '),
                (('Worthi ',),'Worthy '),((' worthie ',' worthi '),' worthy '),
            (('Woulde ','Wolde '),'Would '),((' woldist ',' woldest ',' woulde ',' wolde '),' would '),((' woulde,',' wolde,'),' would,'),((' wolde.',),' would.'),((' woulde:',),' would:'),((' wolde;',),' would;'),
                ((' woundiden',' woundide',' woundid'),' wounded'),((' woundes',' woundis'),' wounds'),((' wounde ',' woude '),' wound '),((' wounde,',),' wound,'),
            ((' woue ',),' wove '),
            ((' wowe ',),' wow '),
        ((' wrapt ',),' wrapped '),
                ((' wrathfull ',' wrothfull '),' wrathful '), ((' wraththe',' wrooth'),' wrath'),
            ((' wreathe',' wrethe'),' wreath'),
                (('wretchidnesse',),'wretchedness'),(('wretchid',),'wretched'),
            ((' wryngeris',),' wringers'),((' wringe ',),' wring '), ((' wryncles',' wrinckles'),' wrinkles'),
                ((' writere',' wryter'),' writer'), ((' writest',' wrytest'),' writest/write'),((' writeth',' wryteth'),' writeth/writes'),
                    ((' wrytynge',' wrytinge',' writynge',' writyng',' wryting'),' writing'),((' wryte ',),' write '), (('wrytten','wrytte','writun','wrytun'),'written'),((' writte ',' writt '),' written '),((' writte:',),' written:'),
            ((' wronge ',' wroge '),' wrong '),((' wronge,',),' wrong,'),((' wronge.',),' wrong.'),((' wroge:',),' wrong:'),
                ((' wroote ',' wroot '),' wrote '),
    (('Iaakob','Iacob'),'Yacob'), (('Iah,',),'Yah,'),(('Jah<',),'Yah<'), (('Iames','James'),'Yames/Yacob'), ((' yarne',),' yarn'), (('Iauan',),'Yavan'),
        (('Yee ','Ye '),'Ye/You_all '),((' ye ',' yee ',' yi '),' ye/you_all '),((' ye,',' yee,'),' ye/you_all,'),((' ye.',' yee.'),' ye/you_all.'),((' ye?',' yee?',),' ye/you_all?'),((' ye:',' yee:'),' ye/you_all:'),((' ye;',' yee;'),' ye/you_all;'),(('(yee ',),'(ye/you_all '), (('Thy ',),'Thy/Your '),((' thi ',' thy '),' thy/your '),#(('>thy ',),'>thy/your '),
            ((' yhe,',),' yea/yes,'), ((' yeres',' yeeris',' yeris'),' years'),((' yeare',' yeere',' yeer',' yere'),' year'), ((' yerned',),' yearned'),
            ((' yelliden',),' yelled'),((' yellyng',),' yelling'),(('Yelle ',),'Yell '),((' yelle ',),' yell '),
                ((' yalowe',),' yellow'),
            (('Hierusalem','Hierusale','Ierusalem','Ierusale','Jerusalem'),'Yerusalem'),
            (('Yis,',),'Yes,'),
                ((' yistirdai',' yisterdai',' yesterdaye',' yestarday'),' yesterday'),
                (('Iesus','Iesua'),'Yesus/Yeshua'),(('Iesu ',),'Yesu '),(('Iesu.',),'Yesu.'),
            (('Yit ',),'Yet '),((' yit ',),' yet '),((' yit,',),' yet,'),((' yit?',),' yet?'),((' yit;',),' yet;'),
            (('Iewrie','Iewry','Iurie','Iury'),'Jewry/Yudea'), (('IEWES','JESEW'),'YEWS'),(('Iewes','Jewis'),'Yews'),#(('Iewes,','Jewis,'),'Yews,'),
            (('Iezreelitesse',),'Yezreelitess'),
        ((' yeelded',' yeldide'),' yielded'),((' yieldeth',' yeeldeth',' yeldith'),' yieldeth/yields'),((' yeldynge',' yeelding',' yeldyng'),' yielding'), ((' yeelde ',' yeeld ',' yelde '),' yield '),((' yelde.',),' yield.'),((' yeeld,',' yelde,'),' yield,'),((' yelde;',),' yield;'),
        (('Ioab',),'Yoab'),
            (('Ioanna','Joone'),'Yoanna'), (('Iohn','Ihon','Joon'),'Yohn'),
            ((' yocke ',' yock ',' yok '),' yoke '),((' yocke,',' yok,'),' yoke,'),
            (('Iordane ','Iordan ','Iorden ','Iorda ','Jordan '),'Yordan '),(('Iordane,','Iordan,','Iorden,','Iorda,','Jordan,'),'Yordan,'),(('Iordane.',),'Yordan.'),(('Iordane:',),'Yordan:'),(('Iordane;',),'Yordan;'),
            (('Ioseph',),'Yoseph'), (('Ioses','Joses'),'Yoses'), (('Iosuah','Iosua'),'Yoshua'),
            ((' yongere',' yonger'),' younger'),((' yongest',' yogest'),' youngest'), (('Yonge ','Yong '),'Young '),((' yonge ',' yong ',' yoge '),' young '),((' yonge,',' yong,',' yoge,'),' young,'),((' yong:',' yoge:'),' young:'),((' yonge)',),' young)'),
                (('Youre ',),'Your '),((' yor ',),' your '),((' youre ',),' your(pl) '),
                ((' yongthe',' yongth'),' youth'),
        (('Iudas','Ivdas','Judas'),'Yudas'), (('Iudah','Judah'),'Yudah'),(('Iuda ','Juda '),'Yudah '), (('Iudea','Judee','Judaea','Judæa'),'Yudea'), (('Iude',),'Yude'),
        (('Ia',),'Ya'),(('Ie',),'Ye'),(('Iu',),'Yu'), # Left-over proper nouns, e.g., Iabes → Yabes
    ((' zeale ',' zele '),' zeal '), ((' zelous ',),' zealous '),
            (('Zebedeus ','zebede ','Zebede '),'Zebedee '), (('Zebedeus,','zebede,','Zebede,'),'Zebedee,'),

    # Middle English complete word substitutions (not just spelling, or else the corrected word is still archaic and will fail a spell-check)
    ((' abak',),' aback'),((' abac.',),' aback.'), # Psa 55:10, 113:3
        ((' abasshed',' abaischid'),' abashed/embarrassed'), # Cvdl/TNT Mrk 16:5
        ((' abode',' abood'),' abode/stayed'), # Wycl Tob 11:14
        ((' abredgide',),' shortened/curtailed'), # Wycl Mrk 13:20
        (('Adamant','Adamat'),'Diamond'),((' adamaunt',' adamant'),' diamond'), # Eze 3:9
        ((' affrighted',),' frightened'), # KJB Mrk 16:6
        ((' alargid',),' enlarged'), # Psa 4:2
            ((' alway ',' allwaie ',' allwaye '),' always '),((' allwaye,',' alway,'),' always,'),((' allwaie.',' alway.',),' always.'),((' allwaye:',' alwaye:',' alway:'),' always:'),((' alway;',),' always;'),
        ((' alayed',),' abated'), # TNT Mrk 4:39
        ((' ambushments',),' ambushes'), # 2Chr 20:22
        (('Anentis',),'Towards'),((' anentis',),' towards'), # Wycl Mrk 10:27, Prov 3:7
        ((' arettid',),' reckoned/counted'), # Hos 8:12
        ((' armeris',),' arms/weapons'),
        (('aseelid',),'sealed'), # Sng 4:12
        ((' aspies',),' in_wait'), # Wycl Mrk 6:19
        ((' aueryce',),' averice/greed'), # Wycl Eze 22:13
        (('avaricious','auerouse'),'avaricious/greedy_for_wealth'), # Ecc 5:9
        ((' avowiden',' avowid'),' avowed/promised'), # Wycl 2Chr 31:6
        # First 'ayen' below has already been substituted above
        (('again biere','ayenbiere',),'redeemer/saviour'),(('ayenbiyng',),'redeeming'),(('ayenbouyte','ayenbouyt'),'bought_back/redeemed'), # Lam 3:58, Hos 7:13
        ((' ayenward',),' to_the_opposite_side'), # Wycl Mrk 4:35
        ((' axyngis',),' askings'),((' axynge',' axyng', ' axen'),' asking'), # Wycl Mrk 10:38 Tob 7:10
    ((' beefes',' beeves',' beeues',),' cattle'), # Wycl 'Num 31:33
        ((' behests',' biheestis'),' behests/promises'), # Ecc 5:4
            ((' behest ',' biheest '),' behest/promise '),
        (('benygnite',),'kindness/mercy'), # Psa 51:5
        ((' besoughte',' bisouyte'),' besought'), # Cvdl 2Chr 33:13
        ((' bethinking',' bithenkynge'),' bethinking/coming_to_think'),((' bethink ',' bethinke '),' bethink/come_to_think '), # Lam 3:21
        (('bethought','bithouyte'),'bethought/came_to_think'),
        (('betokeneth',),'signifies/indicates'), # TNT Mrk 13:14
        (('betrothed','betrouthed'),'betrothed/engaged'), # Deu 20:7
        ((' biclippide',' biclippid'),' took_hold_of'), # # Wycl Mrk 9:35
        ((' bifalle ',),' befall/happen_to '),((' bifelle ',),' befell/happened_to '),((' bifelde',),' befeld/happened_to'), # Lam 5:1, Tob 2:10
        ((' biforknowing',),' foreknowledge'), # # Wycl Deu 29:29
        ((' bihiyten',' bihiyte',' bihiyt',),' promised'), # Wycl Deu 25:19
        ((' birre ',),' force/impetus/wind '), # Wycl Mrk 5:13
        ((' bischop',),' bishop/high-priest'), # Wycl Exo 28:38
        (('bischopriche','bishopricke'),'bishopric/diocese'), # Psa 108:8
        ((' bispete',),' will_spit_at'), # # Wycl Mrk 10:34
        ((' bitakun',),' betaken/committed/entrusted'),((' bitake ',),' betake/give/grant '), # Wycl Jdg 15:12
        ((' bitook',),' betook/entrusted'), # Sng 8:11
        ((' betwixte',' bitwixe',' bitwix',),' between'), # Whcl Deu 1:1
        ((' bewail ',' bewaile ',' bewayle ',' byweile '),' wail_for '), # Lev 10:6
        ((' bewepe ',),' weep_for '), # Lev 10:6
        ((' boldlyer',),' more_boldly'), # TNT Mrk 14:31
        ((' bordis',),' boards/tables'),((' boorde ',' bourde ',' borde ',' boord '),' board/table '),((' boord,',' bord,',),' board/table,'), # Mrk 6:22, 7:28, 11:15
        ((' brasen',' brasun',' brazen'),' bronze'), # Num 16:39
        ((' brech,',),' breeches,'), # Cvdl Jer 13:2
        ((' breidynge',),' pulling'), # Wycl Mrk 9:25
        ((' breigirdil',),' breech-girdle'), # Wycl Jer 13:2
        (('brimstone','brymstoon','brymston'),'brimstone/sulfur'), # Rev 9:17
        ((' broydered',' broidered',' broydred',' broidred'),' embroidered'), # Eze 26:16
            ((' broyder',),' embroider'), # Gnva 2Chr 2:14
        ((' burres',),' burrs/thorns'), # Hos 9:6
        (('buyschementis','buschementis'),'ambushes'), # Jdg 20:36, Lam 4:19
        ((' byssus',),' fine-linen'), # Drby & SLT 2Chr 2:14
        ((' byworde ',),' byword '), # Eze 18:3
    ((' capret',),' she-goat'), # Sng 4:5
        ((' careyn',),' carrion/decaying_body'), # Wycl Deu 21:1
        ((' caul ',' caule ',' kall '),' caul/membrane '), # Lev 3:4, Hosea 13:8
        ((' certis',),' certainly/surely'), # Wycl Tob 9:5
        # 'clepe' -> 'call' is up above
        (('the cheer ',),'the face '), # Lam 3:35
        (('charger',),'platter'), # Mrk 6:28
        (('childiden','childide'),'gave_birth_to'), # Wycl Isa 66:8, Hosea 1:3
        ((' cofynes',' cofyns',),' baskets'), # Wycl Mrk 6:43, 8:19
        # (('cornflooris',),'storage-barns'), # Joel 2:24 Now up at top
        (('comelyngi','comlyngi','comelyng','comeling'),'stranger'), # Wycl Tob 1:7, Isa 54:15
        (('comparisound',),'compared'), # Psa 48:13
        (('Compasse ',),'Compass/Surround '), # Psa 48:12
        ((' coniure',),' call_upon'), # Mrk 5:7
        ((' cockscrow',' cocks crow',),' cocks-crow'),((' cockcrow',' cock crowe',' cock crow',),' cock-crow'), # Mrk 13:35
        ((' cruses',),' clay_pots'), # Mrk 7:8
        ((' culvers',' culueris'),' culvers/pigeons'),((' culver',' culuer'),' culver/pigeon'), # Psa 54:7, Sng 1:14
    ((' dalf ',),' dug '), # Wycl 12:1
        (('dampenede',),'damned/condemned'),((' dampne',),' damn/condemn'), # Wycl originally 'dampnede' Mrk 10:33, Heb 11:7
        # ((' defoulen',),' trampling_on'), # Psa 56:4 already have above as 'defiling'
        (('Deme ',),'Judge '), # Hos 2:2
            (('shall deme ',),'shall judge '),(('thou/you deme?',),'thou/you judge?'),(('To deme ',),'To judge '),(('to deme ',),'to judge '),(('to deme,',),'to judge,'),
                ((' demede',' demed',),' judged'),((' demydist',),' judgest/judge'),((' demeth',),' judgeth/judges'),((' deme ',),' judge/judgement '),((' deme,',),' judge/judgement,'),((' deme.',),' judge/judgement.'),((' deme;',),' judge/judgement;'),
        ((' departyngis',),' departings'), # Lam 3:48
        (('dereworthe','derworth'),'dear/precious'), # Lam 1:2, Luk 3:22
        ((' dight',),' prepare'), # Cvdl Eze 46:24
        (('disparpoilid','disparplid',),'scattered/dispersed'), # Wycl Mrk 3:25, 14:27
        (('domesmen',),'judges/magistrates'), # Wycl Mrk 13:9
        ((' dom ',),' judgement '),((' dom,',),' judgement,'),((' dom;',),' judgement;'), # Lam 3:35,36, Psa 111:5
            ((' doomes',' domes'),' judgements'),((' doom',),' judgement'), # Eze 20:11,36
        ((' dred.',),' dreaded/feared.'), # Ecc 3:14
        ((' drooue',),' herd'), # Wycl Num 7:33
        ((' durste',),' dared'), # Wycl Mrk 12:35
    ((' earthtilieris',),' earth-tillers'), # original was 'erthetilieris' Wycl Mrk 12:7
        ((' eelde',),' age'), # 1Chr 29:28
        ((' eft,',),' after,'), # Wycl Mrk 8:1
        (('Eftsoone',),'Soon_afterward'),(('eftsoone',),'soon_afterward'), # Mat 5:33
        ((' ensample',' ensaumple'),' ensample/example'), # Heb 4:11
        ((' ententifli',),' attentively'),((' ententif',),' attentive'), # Wycl 2Chr 33:13, Lam 4:17
        ((' erid ',),' ploughed '), # Hos 10:13
        ((' Easter ',' ester ',),' Easter/Passover '), # Mrk 14:12
    ((' fallyngis',' fallingis'),' ruins'), # Psa 109:6 The second entry is coz it already gets partially changed above
        ((' fayne ',),' gladly '), # Psa 71:21
        (('ferdful',),'to_be_feared'), # Psa 46:3
        (('fitches',),'cumin_(ISA)_or_spelt_(EZE)'), # KJB Isa 28:25-27, Eze 4:9
        (('fleshhookes','fleshhooks','fleischokis','fleshokes'),'meat-hooks'), # Num 4:14
        ((' forseid',),' aforesaid'), # Tob 1:17
        (('FORSOTHE',),'FOR_CERTAIN/TRULY'),(('Forsothe',),'For_certain/Truly'),((' forsothe',),' for_certain/truly'), # Lev 1:1, Exo 36:34, Mrk 13:37
        ((' forswear ',' forsweare ',' forsuere ',' forswere '),' forswear/perjure ' ), # Mat 5:33
        ((' foundementi',' foundement'),' foundation'), # Lam 4:11, Rev 21:19
        ((' fullyere',),' more_fully'), # Wycl Tob 8:19
    ((' geet,',),' goats,'), # Sng 6:4
        (('gendriden','gendride'),'begat/gave_birth_to'), # Gen 6:4
            (('firste gendrid','first gendrid'),'firstborn'),((' gendrid',),' born'),
        (('Godschest',),'offering_box'), # Cvdl Mrk 12:41
        (('gessiden',),'suppose/imagine'),
        ((' gotte ',' gete '),' gotten '), # Psa 118:15, Hos 2:1
        ((' gobbettes',' gobetis'),' fragments'), # TNT Mrk 6:43
        ((' goteris',),' rain-drops'), # Psa 71:6
        ((' greces',' grecis',),' steps/stairs'), # Psa 123:1
        ((' groyneden',),' murmured/grumbled/complained'), # Wycl Mrk 14:5
        ((' grutchide',),' groutched/grumbled'), # Lam 3:39
    ((' hantch',),' haunch/butcher'), # Psa 7:2
        ((' heestis',),' commands'), # Eze 18:21
        (('Herie ',),'Praise '),((' herie ',' herye '),' praise '), # Psa 148:2
        ((' heuyed',),' heavied/burdened'), # Wycl Mrk 14:40
        ((' hewn',' hewen',' hewun'),' hewn/chopped'),((' heweden',),' hewed/chopped'),((' hewe ',),' hew/chop '), # Psa 73:6, 74:6
        # WHERE/WHAT WAS THIS ((' hilynge',),' hiling/cover_over'),
        ((' hile ',),' cover/protect '), # Wycl Mrk 14:65
        ((' hilide',),' covered/protected'), # Wycl Mrk 16:5
        ((' hiris',),' hires/wages'), # Hos 2:12
        ((' hoor ',),' hoar/gray '), # Hos 7:9
        ((' howbeit',' howebeit'),' howbeit/yet'),((' howbe ',),' howbeit/yet '), # Mrk 6:26
        ((' husbandmen',' hussbandmen',' husband men'),' husbandmen/caretakers'),((' husbandme ',),' husbandmen/caretakers '), # Mrk 12:1
        ((' hyndir',),' rear'), # Mrk 4:38
    ((' iebat',),' gibbet/gallows'), # Wycl Deu 21:22
        ((' impugned',' impugnyde'),' impugned/doubted/disputed'), # Psa 55:2
        (('ingendred',),'ingendered/conceived/born'), # Psa 51:5 Bshps
        (('inkhorn','inkehorne','inckhorne','ynckhorne','ynkhorne'),'ink-horn'), # Eze 9:11
        (('insurrection','insurreccion',),'insurrection/uprising'), # Mrk 3:26
        (('ioyeden',),'enjoyed'), # Psa 113:4
        (('Iles ',),'Isles/Islands '),((' yles',' ylis',' ilis',' iles'),' isles/islands'), (('Ile ',),'Isle/Island '),((' yle ',),' isle/island '),((' yle,',),' isle/island,'),((' yle.',),' isle/island.'), # Eze 27:6
        (('Ilodes',),'Islands'), # Cvdl Isa 59:18
    ((' kids',' kiddes',' kidis'),' kids/young_goats'),((' kid ',' kidde '),' kid/young_goat '),((' kid?',' kidde?'),' kid/young_goat?'), # Sng 1:7, Tob 2:13
            ((' kydney',),' kidney'),
        ((' kittiden ',' kit '),' cut '), # Wycl Mrk 11:8, Eze 37:11 'kit away'
        ((' kittide of ',),' cut off '), # Mrk 14:47
        ((' knaue ',),' knave/dishonest/unscrupulous '),
        ((' knappeth',' knapped'),' struck'), # Psa 46:9
        ((' knowleche ',),' acknowledge '),((' knoulechyng',),' acknowledging'), # Psa 51:11, 110:3
        (('knyytis','kniytis'),'knights/warriors'), # Hos 1:7
        (('knyythod',),'knighthood/army'), # Wycl 2Chr 33:3
    ((' laud ',' laude '),' laud/praise '), # Psa 117:1
        ((' leauynges',' leauings',' levinges'),' left-overs'), # Mrk 8:20
        ((' lechis',),' leeches'), # Wycl Mrk 5:26
        ((' leesyngy',' leesyngi',' leesyng'),' falsehood'), # Hos 7:1 (includes plural)
        ((' leendis',),' loins'), # Wycl Jer 13:2
        ((' lepis',),' baskets'), # Wycl Mrk 8:8
        ((' lese ',),' loose/destroy '), # Wycl Mrk 12:9
        ((' lesewe',),' pasture'), # Eze 34:31
            ((' lesewynge',),' feeding'), # Wycl Mrk 5:11
        ((' letcherie ',),' lechery/lust '),((' letcherie,',),' lechery/lust,'),((' letcherie.',),' lechery/lust.'), # Eze 23:11, Mrk 10:12
        ((' lovedist',),' loved'), # Psa 50:8, Eze 16:37
        (('lustgraues',),'lust-graves'), # Cvdl Num 11:35
    ((' manasside',),' menaced/threatened'), # Wycl Mrk 4:39
        ((' manqueller',),' mankiller/executioner'), # Wycl Mrk 6:27
        (('mansleyingis',),'manslayings/murders'),((' mansleyng',),' manslaying/murder'), # Wycl Mrk 7:22, Num 35:21
        ((' mattokkis',),' mattocks/adzes'),
        ((' maundement',),' commandment'), # Wycl Mrk 7:8
        ((' mawe',),' stomach/innards'), # Wycl Tob 6:5
        ((' mentil',),' mantle'), # Wycl Num 4:6
        ((' meten',),' measure_out'),((' metun',),' measured_out'), # Wycl Mrk 4:24
        ((' meynees',),' households/companies'),((' meynee',),' household/family'), # 1Chr 9:13, Num 36:!2
        ((' miche.',),' much.'), # Lam 3:23
        ((' minished',),' diminished'),((' diminishe',' mynyshe',' minishe',' mynish',),' diminish'), # Psa 107:39, Ecc 5:16
        (('morewtidi','morewtid'),'morning'), # Psa 62:7
        ((' moun ',),' may/can '),((' moun,',),' may/can,'),((' moun.',),' may/can.'),((' moun;',),' may/can;'), # Wycl Pro 3:15, 5:6, Mrk 10:39
    (('nativity','natyuyte','natiuitie'),'nativity/birth'),
        (('neiyidist','neiyede'),'came_near'),((' neiye ',),' come_near '), # Wycl Lam 3:57, 4:18, Tob 6:8
            ((' neiyeth',' neiyith'),' approacheth/approaches'), # Eze 18:6, 30:3
        ((' nolden',' nolde'),' wouldn’t'), # Wycl Isa 65:12, Hos 11:5
        ((' nollis',),' necks'), # Wycl Lev 26:13
        (('Nyle',),'Not/Don’t'),((' nyle',),' won’t'), # Psa 74:5, 1 Cor 10:1
    ((' obeschen',),' obeys'), # Wycl Mrk 4:40
        ((' offscouring',' ofscouring'),' offscouring/outcasts'), # Lam 3:45
        ((' ordures ',),' dung '), # Tob 2:11
        ((' outakun',),' out-taken/except'), # Hos 13:4
    (('Pask ',),'Passover '),((' pascall',' paske',' pask'),' passover'), # Wycl 2Chr 30:2,5, Mrk 14:1
        (('(percase)',),'(perchance)'), # Lam 3:29
        ((' peiryng',),' injuring'), # Wycl Mrk 8:36
        ((' peisynge',),' weighing'), # Wycl Num 7:74
        ((' pitouse',),' piteous'), # Wycl 2Chr 30:9
        ((' polld',),' clipped'), # RV Jer 9:26 originally 'polled'
        ((' preciousere',),' more_precious'), # Wycl Prov 3:15
        ((' prijs',),' price'), # Wycl Lev 27:12
        (('prynshode',),'princely_dignity'), # Wycl Mrk 10:42
        ((' puissant',),' powerful'),((' puissaunce',),' power'), # Psa 76:4
        ((' purueiede',),' purveyed/supplied'),((' purveyor',' purueyour'),' purveyor/buyer'), # Wyc Eze 20:6, Tob 1:13
        ((' puruyaunce',),' providence'), # Ecc 5:5
    ((' quadrin',),' small_coin/farthing'), # Gnva Mrk 12:42
        ((' quyk ',),' quick/living '),((' quyk,',),' quick/living,'),((' quyk;',),' quick/living;'), # Wycl Heb 4:11
        ((' quicken ',' quykene ',),' quicken/bring_back_to_life '),
    ((' ravin',' rauine',' raueyn'),' ravin/plunder_or_prey'),
        ((' reckist ',),' reckons_with/takes_notice_of '), # Wycl Mrk 12:14
        ((' rehedes',),' reeds/rods/cubits'), # Wycl 45:1
        ((' relifs',),' remains/fragments'), # Wycl Isa 10:21
        ((' rent ',' rente ',' reende '),' rent/tear '), # Lev 10:6
        ((' reuth ',),' pity/sorrow '),
        ((' riynde ',),' rind/bark '),
        ((' rooch ',),' rock '), # Psa 113:8
    ((' salewis',),' willows'), # Wycl Isa 15:7
        ((' savegard',),' life-guard'), # Gnva Eze 38:7 originally 'sauegard'
        ((' scall',' skall'),' scall/scab'), # LEv 13:37
        (('schapide',),'created/formed'), # Wycl Heb 11:7
        (('schaplynesse',),'shapeliness/beauty'),
        (('schedde ',),'separated/poured '), # Lam 4:11
        (('schenschipis','schenshipis'),'harm/troubles'),(('schenschipe',),'harm/trouble'),(('schenschipfuli',),'disgracefully/ruinously'),(('schenschip',),'disgrace/ruin'), # Psa 56:4, 78:12
        ((' schent',),' harmed/shamed'),
        (('schynyngere',),'more_shiny'),
        ((' scrippe',),' bag/satchel'), # Wycl Tob 8:2
        ((' sepulture',),' burial'), # Tob 1:20
        ((' settiden ',),' set/placed '),((' settidist ',),' set/place '), # Joel 3:3, Psa 49:18
        (('shamefulere',),'more_shameful'), # Eze 22:10 originally 'schamefulere'
        ((' shawmes',),' shawm_instruments'),((' shaume ',),' shawm_instrument '), # Hos 5:8
        (('shewtoken',),'sign'), # Eze 12:11
        (('Shittim','Sittim','Sechim'),'Acacia'),((' shittim',' setim'),' acacia'), # Deu 10:3
        ((' sithen',' sith',),' since'), # Wycl Mrk 9:20
        (('syngeressis',),'female_singers'), # Ecc 2:8
        ((' sleeresse',),' slayers'),((' sleere',' sleeri'),' slayer'), # Hos 9:13, Eze 21:14
        ((' slowen',),' slayed'), # Wycl Mrk 12:5
        ((' socoure,',),' security,'), # Cvdl Psa 78:35
        (('sour dowy','sowrdowy'),'sourdough/leaven'), # 'sowre' is already 'sour' Wycl Mrk 8:15
        ((' spakest',' spakist'),' spakest/spake'), # Psa 49:20
        (('Nard pisrike',),'Spikenard/Nard'),((' spikenarde',),' spikenard/nard'),((' spikenard ',),' spikenard/nard '),((' spikenard,',),' spikenard/nard,'), # Mrk 14:3
        (('spoused','spowside'),'spoused/engaged'), # Deu 20:7
        ((' spuyle ',),' spoil/strip '), # Hos 2:3
        ((' stablished',),' strengthened/made_firm'), (('Stablish',),'Strengthen'),((' stablish',),' strength/make_firm'),
        ((' stater',),' coin'),
        ((' stien ',' stie '),' ascend/descend '), # Mrk 10:33
        ((' stolis',),' stoles/long_garments/robes'), # Wycl Mrk 12:38
        ((' stonying',),' astonishment'), # Wycl Mrk 5:42
        ((' straygtly',),' straightly'), # TNT Mrk 3:12
        (('straightwayes','straightwaye'),'straightway/immediately'), # Gnva Mrk 4:16, 6:25
        ((' stronde',),' stream/river'), ((' strondis ',),' riverbeds '),
        (('symylacris',),'images'), # Hos 11:2 (see Latin)
        ((' soupid',),' supped/eaten'),((' soupyng',),' supping/eating'), # Wycl Tob 8:1, Mrk 14:15
    ((' tabrets',' tabrettes',),' tabrets/tambourines'), # Jer 31:4
        ((' thankyngis',),' thankings'), # Wycl Tob 2:14
        (('the goodman','the good man'),'the master'), # Mrk 14:14
        ((' therf ',),' unleavened '), # Wycl 2Chr 35:17
        ((' tillers',' tilieris'),' tillers/farmers'), # Wycl Mrk 12:1
        (('to-breke',),'break'),(('tobrokun',),'broken_to_pieces'), # Wycl Isa 43:17, Eze 13:21
        ((' toon ',),' toe '), # Wycl Mrk 10:37
        ((' torente',),' tore/ripped_apart'), # Wycl Mrk 14:63
        ((' tother',),' other'), # Lev 23:15
        ((' be as towe',' be as tow'),' be as wick/kindling'),((' like as towe',),' like as wick/kindling'),((' quenched as towe',' quenched as tow'),' quenched as wick/kindling'), # Isa 43:17
        ((' tretiden',),' argued'), # Wycl Mrk 9:32
        ((' tristili',),' confidently'),((' trist,',),' trusted,'), # Wycl Jer 23:6, 2Chr 32:10
        (('troublous',),'troubled'), # Psa 46:3
        ((' turnen ',),' turn '), # Wycl 2Chr 30:9
        (('twystinge',),'tweeting'), # Sng 2:12
    # 'v' is already changed to 'u' above
    ((' unhiliden',),' unhid/discovered'), # Wycl Eze 22:10
        ((' unknowe',),' not_know'), # Wycl 1Cor 10:1
        ((' unnethis',),' scarcely/barely'), # Wycl Tob 2:8
        ((' unpitouse',),' impious/wicked'), # Wycl Prov 13:2
        ((' unpossible',' unpossyble'),' impossible'), # Mrk 10:@7
        ((' unschamefastli',),' shamelessly'), # Wycl Eze 23:11
        ((' unschamefast',),' shameless'), # Wycl Eze 3:7
        (('unobedient',),'disobedient'), # Cvdl Eze 12:3
        ((' unpitee',),' unpity/not_pity'), # Wycl Eze 7:11
        ((' usurere ',),' usurer/money-lender '), # Psa 108:11
        ((' unyuersite',),' university'), # Wycl Tob 8:19
    ((' vengere',),' avenger'), # Wycl Jer 51:56
        ((' venie ',),' avenge '), # Wycl Deu 32:43
        (('Verily','Verely','Veryly','Uerily','Ueryly','Uerely'),'Verily/Truly'),((' verily',' verelye',' verely',' veryly',' verili'),' verily/truly'), # Psa 57:2
            ((' verie',),' very/true'), # TNT Mrk 11:32
        ((' verity',' veritie',' verite'),' verity/truth'), # Psa 111:7
        ((' vertues',),' hosts/armies'),((' vertu',),' power/strength'),
        ((' viliche',),' vilely'), # Wycl Deu 25:3
        ((' vytale',),' vital(s)/essential(s)'),
    ((' warpe',),' warp'),((' warp',),' warp/weave'), # Lev 13:59
        ((' waschun',),' washed'), # Wycl Mrk 10:39
        ((' waxed',' wexed'),' waxed/grew'),((' waxeth',' waxith',' wexith'),' waxeth/waxes/grows'),((' wexe ',),' wax/grow '), # Psa 89:6, Mrk 4:32
        ((' welewide',),' withered'), # Wycl Mrk 4:6
        ((' weltred',),' overturned'), # Cvdl Mrk 9:20
        ((' wem',),' spot/blemish'), # Wycl Num 28:31
        ((' whence ',' whennus ',' whannus ',' whens ',' whece '),' whence/where '), # Psa 120:1, Mrk 6:2
        ((' whensoever',' whensoeuer'),' whenever'), # Mrk 9:18
        (('Whereunto','Wherevnto','Wherunto'),'Whereunto/To_what'), # Mrk 4:30
        ((' whett ',' whet '),' sharpen '), # Ecc 10:10
        ((' wiste',' wist'),' knew'), # Mrk 7:24, 14:40
        ((' witynge',),' knowing'), # Wycl Mrk 12:15
        ((' wite ',),' wit/know '),((' wite,',),' wit/know,'),((' wite.',),' wit/know.'),((' wite;',),' wit/know;'), # Wycl 1Ki 20:13, Isa 41:22
        (('withall','withal'),'also/fully'), # Mrk 10:39
        (('withoutforth',),'out_and_about'), # Wycl Eze 34:21
        (('wlappid',),'wrapped'), # Wycl 16:4
        ((' wolden',),' wanted'), # Wycl Mrk 9:12,29
        ((' wolt',),' wilt/will'), # Wycl Tob 3:10
        ((' wont',),' want/accustomed'), # KJB,Wycl Mrk 10:1
        ((' woofe',' oof'),' woof'),((' woof',),' woof/knit'), # Lev 13:59
        (('woode droncken',),'madly drunken'), # Hos 7:5
        (('woodnesse',),'madness/wildness'), # Isa 13:9
        (('wormewoode','wormewood','wormwod','wermod'),'wormwood'),
        ((' woost',' wost'),' know'),((' woot',),' knows'), # Wycl Eze 37:3, Mrk 13:32
        ((' wrogeous',),' so_wrong'), # Psa 119:134
        (('wroughtest','wrouytist'),'wroughtest/do'),(('wrought','wrougth','wrouyten','wrouyte','wrouyt'),'wrought/done'), # Eze 18:19
        ((' wrutt ',),' rooted '), # Cvdl Psa 80:13
        ((' wydenesse',),' width'), # Cvdl Eze 41:1
        ((' wyndewid',),' winnowed/blown'), # Wycl Eze 36:19
    ((' yeden',),' walked/went'), # Wycl Eze 1:14
        ((' yerde',),' rod/stick'), # Wycl Psa 109:2
        ((' yerdis',),' sticks_or_staffs'),
        ((' ylyon',),' flank/side_of_stomach'), # Wycl Lev 3:4
        ((' yonglyng',),' youth'), # Wycl Mrk 16:5
    # 'Yiue', 'yeuen', etc., are under ' gave ' above

    (('iia',),'iya'), # e.g., Abiiah → Abiyah
    (('Iio',),'Iyo'), # e.g., Iion → Iyon (1Ki 15:20)
    (('tiō ',),'tion '), # e.g., dedication Dan 3:3

    (('auites ',),'avites '),(('auites,',),'avites,'), # e.g., Dehauites → Dehavites, Ezr 4:9
    (('euites ',),'evites '),(('euites,',),'evites,'), # e.g., Archeuites → Archevites, Ezr 4:9

    # Roman numerals
    ((' i ',),' 1 '), ((' .ii.',' ii.',' ij.'),' 2'), (('.iii.',),'3'), ((' .iiii.',' iiij.'),' 4'),((' iiij ',),' 4 '),
            ((' .v.',' v.'),' 5'), ((' .vi.',' vj.'),' 6'), ((' vij',),' 7'),(('.vii.','vii.'),'7'), ((' viij',),' 8'),
        ((' .x.',' x.',),' 10'), (('.xii.',),'12'),((' xii.',' xij.'),' 12'),((' xiiij',),' 14'),
        ((' xxvij.',),' 27'),
        ((' xx.',),' 20'), ((' xl ',),' 40 '),((' xl.',),' 40'),((' LX.',),' 60'),((' lx.',),' 60'),((' lxxv.',),' 70'),
        ((' xxx.',),' 30'),
        ((' xxv.M. ',' xxv M ',),' 25,000 '),((' x M ',),' 10,000 '), ((' .M. ',' M. '),' 1,000 '), ((' XC. ',),' 90 '),((' XL. ',),' 40 '),
        ((' XXIII',),' 23'),
        ((' lxxx.',),' 80'),
        (('v.C. ',),'five_hundred '),
        (('.ii.M.',),'2,000'),

    # Symbols
    (('& ',),'and '),

    # Proper nouns
    (('Absolon',),'Absolom'),
    (('Alpheus','Alphey','Alfey','Alphee'),'Alphaeus'),(('Alphe ',),'Alphaeus '),(('Alphe,',),'Alphaeus,'), # Mrk 3:18
    (('Assiriens',),'Assyrians'),
    (('Baalim','Baalym'),'Baals'),
        (('Babels',),'Babel’s'),
        (('Babiloyne','Babilon'),'Babylon'),(('Babilo ',),'Babylon '),(('Babilo,',),'Babylon,'),
    (('Barne ',),'Barnea '),
    (('Bartholomewe','Bartlemew','Bartylmew'),'Bartholomew'), # Mrk 3:18
    (('Belzebub','Belsabub'),'Beelzebub'), # Mrk 3:22
    (('Bethania','Bethanie','Bethanye','Betanye'),'Bethany'),
    (('Cananite',),'Canaanite'), # Mrk 3:18
    (('Cades ',),'Kadesh '),
    (('Capharnaum','Cafarnaum'),'Capernaum'), # Wycl Mrk 1:21
    (('Cesarye','Cesarea'),'Caesarea'), # Wycl Mrk 8:27
        (('Cæsar','Cesar'),'Caesar'),
    (('Danyel',),'Daniel'),
    (('Decapoleos',),'Decapolis'), # Wycl Mrk 7:31
    (('Elias','Helyas'),'Elias/Elijah'),(('Helie','Elie'),'Elye/Elijah'), # Mrk 6:15
    (('Hester',),'Esther'),
    (('Ysaie','Esay'),'Isaiah'), # Mrk 7:6
    (('Idumaea','Edoma'),'Idumea'),(('Idume,',),'Idumea,'), # Mrk 3:8 ('Yd' is already changed to 'Id' above)
    (('Erodias',),'Herodias'), # Mrk 6
    (('DARIVS',),'DARIUS'),
    (('Ephpheta','Effatha','Ephatha','Effeta','ephatha',),'Ephphatha'), # Mrk 7:34
    (('Eue',),'Eve'), # KJB-1611 Tob 8:6
    (('Galilea ','Galile ',),'Galilee '),(('Galile,',),'Galilee,'),(('Galile.','Galil.'),'Galilee.'),(('Galile:',),'Galilee:'),(('Galile;',),'Galilee;'),
    (('Genesareth','Genasareth','Genezareth'),'Gennesaret'),
    (('Gethsamany','Gethsemani'),'Gethsemane'),
    (('Grece',),'Greece'),(('Greeke','Greke'),'Greek'),
    (('Herode','Eroude'),'Herod'),
    (('Isahac','Isaak','Ysaac'),'Isaac'),
    (('Israels',),'Israel’s'),
    (('IESVS',),'JESUS'), (('IEVVES',),'JEWS'), # Gnva Mat 27:37
    (('Jayrus',),'Yairus'),
    (('Jeremye',),'Jeremiah'), # Wycl or should that be 'Yeremye'
    (('Kadesh Barnea',),'Kadesh-barnea'),
    (('Marck','Marke'),'Mark'), #(('Marck ','Marke '),'Mark '),(('Marke,',),'Mark,'), # Act 12:12
    (('Matthewe','Mathew','Matheu'),'Matthew'), # Mrk 3:18
    (('Medeis',),'Medes'),
    (('Nephthali','Neptalym','Nephtali'),'Naphtali'),
        (('Nabuchodonosor','Nabugodonosor','Nebuchadnezar'),'Nebuchadnezzar'),
        (('Nineueh','Niniue','Nynyue','Nineue',),'Nineveh'),(('Nineve,',),'Nineveh,'),(('Ninive.','Nineve.'),'Nineveh.'),
    (('Petre','Petir'),'Peter'),
    (('SALOMON',),'SOLOMON'),(('Salomon',),'Solomon'),
    (('Samarie',),'Samaria'),
    (('Sare',),'Sara'),
    (('Sata:',),'Satan:'), # Bshps Mrk 8:33
    (('Sydon',),'Sidon'), # Mrk 7:24
    (('Thaddeus','Taddeus','Thadee'),'Thaddaeus'), # Mrk 3:18
    (('Tigrys',),'Tigris'),
    (('IEHOVAH','IEHOUAH'),'YEHOVAH'),(('Iehouah',),'Yehovah'),
    (('Syon','Sion'),'Zion'),

    # Generalised left-overs
    (('edist ','idist '),'ed '),(('edst ',),'ed '), # e.g., washedist, paintedst, deckedst from Eze 23:40
    (('nesse ',),'ness '),(('nesse,',),'ness,'),(('nesse.',),'ness.'),(('nesse:',),'ness:'),(('nesse;',),'ness;'),
    (('ynge ','yng '),'ing '),(('ynge,','yng,'),'ing,'),(('ynge.','yng.'),'ing.'),(('ynge:','yng:'),'ing:'),(('ynge;','yng;'),'ing;'),
    )
oldWords, newWords = [], []
for wordMapEntry in ENGLISH_WORD_MAP:
    assert len(wordMapEntry) == 2, f"{wordMapEntry}"
    someOldWords,newWord = wordMapEntry
    assert isinstance( someOldWords, tuple ), f"{someOldWords=} should be a tuple"
    assert isinstance( newWord, str )
    if '/' in newWord: assert newWord.count( '/' ) <= 2, f'Too many forward slashes: {someOldWords=} {newWord=}'
    for sowIx,someOldWord in enumerate( someOldWords ):
        assert isinstance( someOldWord, str ) and len(someOldWord)>=2, f"{someOldWord=}"
        assert someOldWord != newWord, f"Attempting to replace identical English word: {someOldWord=}"
        assert someOldWord not in oldWords, f"duplicate oldWord: {someOldWord=} ({newWord=})"
        if someOldWord not in (', prophecie,',', prophesie,'): assert someOldWord[0] != ',', f"{someOldWord=}" # Typo
        if 1 or '_' not in someOldWords[0] and '_' not in newWord:
            if someOldWords[0].startswith(' ') or newWord.startswith(' '): assert someOldWord.startswith(' '), f"Mismatched leading space: {someOldWords[0]=} {someOldWord=} {newWord=}"
            else: assert not someOldWord.startswith(' '), f"Mismatched leading space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        if someOldWords[0].endswith(' ') or newWord.endswith(' '): assert someOldWord.endswith(' '), f"Mismatched trailing space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        else: assert not someOldWord.endswith(' '), f"Mismatched trailing space: {someOldWords[0]=} {someOldWord=} {newWord=}"
        if sowIx > 0: assert someOldWord not in newWord, f"Recursive substitution of '{someOldWord}' into '{newWord}' (might need to be moved to first position in list)"
        if someOldWord[-1] in ' ,.:;)' and someOldWord not in ('.ii.M.',):
            assert newWord[-1] == someOldWord[-1] or newWord.strip().isdigit(), f"Mismatched trailing character: {someOldWord=} {newWord=}"
        assert '  ' not in someOldWord, f"{someOldWord=}"
        oldWords.append( someOldWord)
    # We check these, not because it's really a problem, but just to catch a few types of accidental errors, i.e., to confirm that it's intentional
    if newWord not in (' 40 ',' 60',
                       ' abated',' afar,',' among ',' and ',
                       ' baskets',' between',' burial', ' can ',' cattle',' clipped',' covered',' cut ',
                       ' diamond', 'ed ',
                       ' feeding',' fragments','grape-gatherers', ' herd', 'immediately',' loved',
                       ' other', ' pasture',' power',' promised',
                       ' reckoned/counted',' ruins',
                       'scattered', 'stiff-necked', 'stranger',
                       'themselves','throughout',' towards',' turn ',' youth',
                       ' washed','whithersoever','whosoever',' hosts/armies','thyself/yourself'
                       ): # sometimes two→one and sometimes it's a single word
        assert newWord not in newWords, f"Duplicated {newWord=}"
    if someOldWords[0].startswith(' '): # and '_' not in someOldWords[0] and '_' not in newWord:
        assert newWord.startswith(' '), f"Mismatched leading space:  {someOldWords} {newWord=}"
    if someOldWords[0].endswith(' '): assert newWord.endswith(' '), f"Mismatched trailing space: {someOldWords} {newWord=}"
    if newWord[-1] in ' ,.:;)':
        for someOldWord in someOldWords:
            if someOldWord not in ('fitches',):
                assert someOldWord[-1] == newWord[-1] or newWord.endswith('(s)'), f"Mismatched trailing character: {someOldWords} {newWord=}"
    assert '  ' not in newWord, f"{newWord=}"
    newWords.append( newWord )
print( f"Have {len(oldWords):,} old words -> {len(newWords):,} modern English words.")
del oldWords, newWords


def moderniseEnglishWords( htmlStr:str, allowOptions:bool|None=False ) -> str:
    """
    Convert ancient English spellings to modern ones.

    May return something like 'endureth/endures' if allowOptions is set.

    This has been used for KJB-1769, KJB-1611, Biships Bible, Geneva Bible, Coverdale Bible,
        and middle-English Wycliffe Bible.

    Text in htmlStr parameter can be inside a span,
        e.g., '<span class="Wycl_verseTextChunk">ech man in his seruice, and in the offring,</span>'
    """
    fnPrint( DEBUGGING_THIS_MODULE, f"moderniseEnglishWords( ({len(htmlStr)}) )" )

    # lastHtmlStr = htmlStr
    for oldWords,newWord in ENGLISH_WORD_MAP:
        if not allowOptions and '/' in newWord:
            assert newWord.count( '/' ) == 1, f'Too many forward slashes: {oldWords=} {newWord=}'
            newWord = newWord.split( '/' )[1].replace('_or_','/') # Eliminate the first option and the forward slash (but maybe add a new forward slash)
        for oldWord in oldWords:
            htmlStr = htmlStr.replace( oldWord, newWord )
            # if a word is enclosed by space(s), also try angle brackets in case it's in a <span>word<span> sequence
            if newWord[0] == ' ':
                htmlStr = htmlStr.replace( f'>{oldWord[1:]}', f'>{newWord[1:]}' )
            if newWord[-1] == ' ':
                htmlStr = htmlStr.replace( f'{oldWord[:-1]}<', f'{newWord[:-1]}<' )
                if newWord[0] == ' ': # then it has a space at both ends
                    htmlStr = htmlStr.replace( f'>{oldWord[1:-1]}<', f'>{newWord[1:-1]}<' )
        #     if htmlStr != lastHtmlStr and 'COMMON' in htmlStr:
        #         print( f"{oldWord=} {newWord=} {htmlStr=} {lastHtmlStr=}")
        # lastHtmlStr = htmlStr

    return htmlStr
# end of OldBiblicalEnglish.moderniseEnglishWords



def briefDemo() -> None:
    """
    Main program to handle command line parameters and then run what they want.
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the spelling converter
    pass
# end of OldBiblicalEnglish.briefDemo

def fullDemo() -> None:
    """
    Full demo to check class is working
    """
    BibleOrgSysGlobals.introduceProgram( __name__, PROGRAM_NAME_VERSION, LAST_MODIFIED_DATE )

    # Demo the spelling converter
    allowOptions = True
    originalString = ' deuine '
    expectedResultString = ' divine '

    newString = lastString = originalString
    for oldWords,newWord in ENGLISH_WORD_MAP:
        if not allowOptions and '/' in newWord:
            assert newWord.count( '/' ) == 1, f'Too many forward slashes: {oldWords=} {newWord=}'
            newWord = newWord.split( '/' )[1].replace('_or_','/') # Eliminate the first option and the forward slash (but maybe add a new forward slash)
        for oldWord in oldWords:
            newString = newString.replace( oldWord, newWord )
            if newString != lastString:
                print( f"  AA After {oldWord=} to {newWord=} with {lastString=} from {originalString=}, got {newString=}")
                lastString = newString
            # if a word is enclosed by space(s), also try angle brackets in case it's in a <span>word<span> sequence
            if newWord[0] == ' ':
                newString = newString.replace( f'>{oldWord[1:]}', f'>{newWord[1:]}' )
                if newString != lastString:
                    print( f"  BB After {oldWord=} to {newWord=} with {lastString=} from {originalString=}, got {newString=}")
                    lastString = newString
            if newWord[-1] == ' ':
                newString = newString.replace( f'{oldWord[:-1]}<', f'{newWord[:-1]}<' )
                if newString != lastString:
                    print( f"  CC After {oldWord=} to {newWord=} with {lastString=} from {originalString=}, got {newString=}")
                    lastString = newString
                if newWord[0] == ' ': # then it has a space at both ends
                    newString = newString.replace( f'>{oldWord[1:-1]}<', f'>{newWord[1:-1]}<' )
                    if newString != lastString:
                        print( f"  DD After {oldWord=} to {newWord=} with {lastString=} from {originalString=}, got {newString=}")
                        lastString = newString
    print( f"Started with {originalString} ({allowOptions=}) and finished with {newString=}\n")
    assert newString == expectedResultString

    for testHTMLStr,expectedResultStr in (('Iewrie','Jewry/Yudea'),
                                          ('prophecied','prophesied'),
                                          ('Reioycing','Rejoicing'),
                                          ('vnclennesses','uncleannesses'),
                                          ('COMMONLI CALLED','COMMONLY CALLED')):
        resultStr = moderniseEnglishWords( testHTMLStr, allowOptions=True )
        assert resultStr == expectedResultStr, f"moderniseEnglishWords({testHTMLStr}) gave {resultStr=} instead of {expectedResultStr=}"
# end of OldBiblicalEnglish.fullDemo

if __name__ == '__main__':
    from multiprocessing import set_start_method, freeze_support
    set_start_method('fork') # The default was changed on POSIX systems from 'fork' to 'forkserver' in Python3.14
    freeze_support() # Multiprocessing support for frozen Windows executables

    # Configure basic Bible Organisational System (BOS) set-up
    parser = BibleOrgSysGlobals.setup( SHORT_PROGRAM_NAME, PROGRAM_VERSION, LAST_MODIFIED_DATE )
    BibleOrgSysGlobals.addStandardOptionsAndProcess( parser )

    fullDemo()

    BibleOrgSysGlobals.closedown( PROGRAM_NAME, PROGRAM_VERSION )
# end of OldBiblicalEnglish.py
