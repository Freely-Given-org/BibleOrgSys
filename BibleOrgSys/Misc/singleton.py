#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# singleton.py
#   Last modified: 2010-12-15
#
# Taken from http://en.wikipedia.org/wiki/Singleton_pattern
#
# Can be used as a Python decorator in order to force a class to only ever have one instance
#
#       from BibleOrgSys.Misc.singleton import singleton
#
#       @singleton
#       class MyClass:
#           …


def singleton(cls):
    instance_container = []
    def getinstance():
        if not len(instance_container):
            instance_container.append(cls())
        return instance_container[0]
    return getinstance

# end of singleton.py
