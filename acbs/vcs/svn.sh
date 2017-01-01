# notice: on error, an error code should be returned by `exit` or `return`
# - return value: print to std output in utf-8
# creating new functions is allowed, but don't delete necessary ones.

# vcs_repofetch: accepts 2 args: 1. URL 2. dest folder
# - return plain URL
#
vcs_repofetch() {
	svn co $1 $2
}

# vcs_switchbranch: accepts 1 arg: 1. new branch
vcs_switchbranch() {
	svn switch $1
}

# vcs_switchcommit: accepts 1 arg: 1. revision
vcs_switchcommit() {
	svn up -r$1
}

# vcs_repoupdate: accepts no arg
# - return nothing
# - remark - you may want to check if conflicts exist
vcs_repoupdate() {
	svn up
}

# vcs_test: accepts no arg
# To test vcs software existence
# - exit with 0 if exist, on any error exit with other code
vcs_test() {
	if type -p svn; then
		exit 0
	else
		exit 127
	fi
}

# vcs_repourl: accepts 1 arg: 1. folder
# - return: primary pull url of the given repo
# - remark - please try to redirect other possible output to `/dev/null`
#
vcs_repourl() {
   echo "?"
}
