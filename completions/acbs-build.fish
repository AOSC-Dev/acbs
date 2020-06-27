function __acbs_complete_package
    set tree (acbs-build -q 'tree:default' 2>/dev/null)
    if test $status != 0
        return
    end
    if test -z $tree -o ! -d $tree
        return
    end
    find "$tree/groups/" -maxdepth 1 -mindepth 1 -type f -printf 'groups/%f\n'
    if string match -q -- "*/*" "$current"
        return
    end
    find "$tree" -maxdepth 2 -mindepth 2 -type d -not -path "$tree/.git" -printf '%f\n'
end

function __acbs_complete_tree
    set forest (acbs-build -q 'path:conf' 2>/dev/null)/forest.conf
    if test $status != 0
        return
    end
    gawk 'match($0,/\[(.*)\]/,m) {print m[1]}' "$forest"
end

complete -c acbs-build -f

complete -c acbs-build -s v -l version -d 'Show the version and exit'
complete -c acbs-build -s d -l debug -d 'Increase verbosity to ease debugging process'
complete -x -c acbs-build -s t -l tree -d 'Specify which abbs-tree to use' -a "(__acbs_complete_tree)"
complete -c acbs-build -s q -l query -d 'Do a simple ACBS query'
complete -c acbs-build -s c -l clear -d 'Clear build directory'
complete -c acbs-build -s k -l skip-deps -d 'Skip dependency resolution'
complete -c acbs-build -s g -l get -d 'Only download source packages without building'
complete -c acbs-build -s r -l resume -d 'Resume a previous build attempt' -a "(__fish_complete_path)"
complete -c acbs-build -a "(__acbs_complete_package)"
