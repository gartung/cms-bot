#!/bin/bash -e
env > run.log
ld.so --help | grep supported | grep x86-64-v
mkdir matrix
pushd matrix
  runTheMatrix.py --job-reports --command " -n 5 --customise Validation/Performance/TimeMemorySummary.customiseWithTimeMemorySummary " \
                  -i all -s -j 1 --ibeos >>../run.log 2>&1 || touch runall-report-step123-.log
  for f in $(find . -name '*' -type f) ; do
    case $f in
      *.xml|*.txt|*.log|*.py|*.json|*/cmdLog ) ;;
      * ) rm -rf $f ;;
    esac
  done
popd
tar -czvf matrix.tar.gz matrix >>run.log 2>&1
mv matrix/runall-report-step123-.log matrix.log
grep -E ' Step[0-9]' matrix.log || true
grep ' tests passed' matrix.log || true
