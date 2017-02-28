python3 -m cProfile -o playscii.profile playscii.py "$1" "$2" "$3"
gprof2dot -f pstats playscii.profile | dot -Tpng -o profile.png
