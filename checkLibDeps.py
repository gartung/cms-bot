#!/usr/bin/env python
# TODO is this file used?
from __future__ import print_function

import os
import re


class LibDepChecker(object):
    def __init__(self, startDir=None, plat='slc6_amd64_gcc493'):
        self.plat = plat
        if not startDir:
            startDir = os.getcwd()
        self.startDir = startDir

    def doCheck(self):
        import glob
        pkgDirList = glob.glob(self.startDir + '/src/[A-Z]*/*')
        errMap = {}
        for pkg in pkgDirList:
            if not os.path.isdir(pkg):
                continue
            pkg = re.sub('^' + self.startDir + '/src/', '', pkg)
            missing = self.checkPkg(pkg)
            if missing:
                errMap[pkg] = missing

        from pickle import Pickler
        summFile = open('libchk.pkl', 'wb')
        pklr = Pickler(summFile, protocol=2)
        pklr.dump(errMap)
        summFile.close()

    def checkPkg(self, pkg):
        libName = 'lib' + pkg.replace('/', '') + '.so'
        if not os.path.exists(self.startDir + '/lib/' + self.plat + '/' + libName):
            return []
        cmd = '(cd ' + self.startDir + '/lib/' + self.plat + ';'
        cmd += 'libchecker.pl ' + libName + ' )'
        print("in ", os.getcwd(), " executing :'" + cmd + "'")
        log = os.popen(cmd).readlines()
        return log


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--platform', default=None)
    parser.add_argument('-n', '--dryRun', default=False, action='store_true')
    parser.add_argument('-d', '--startDir', default=None)
    args = parser.parse_args()

    # Keeping it for interface compatibility reasons
    # noinspection PyUnusedLocal
    dryRun = args.dryRun
    plat = args.platform or os.environ['SCRAM_ARCH']
    startDir = args.startDir or '.'

    ldc = LibDepChecker(startDir, plat)
    ldc.doCheck()


if __name__ == "__main__":
    main()
