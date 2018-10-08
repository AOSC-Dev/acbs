# notice: on error, an error code should be returned by `exit` or `return`
# - return value: print to std output in utf-8
# creating new functions is allowed, but don't delete necessary ones.

# vcs_repofetch: accepts 3 args: 1. URL 2. dest folder 3. depth
# - return plain URL
#
vcs_repofetch() {
	if [[ ! -z $3 ]]; then
		git clone --recursive --depth $3 $1 $2
	else
		git clone --recursive $1 $2
	fi
}

# vcs_switchbranch: accepts 1 arg: 1. new branch
vcs_switchbranch() {
	git checkout $1
}

# vcs_switchcommit: accepts 1 arg: 1. commit hash
vcs_switchcommit() {
	git checkout $1
}

# vcs_repoupdate: accepts 1 arg: 1. new URL
# - return nothing
# - remark - you may want to check if conflicts exist
vcs_repoupdate() {
	git pull $1
	git submodule update --recursive
}

# vcs_test: accepts no arg
# To test vcs software existence
# - exit with 0 if exist, on any error exit with other code
vcs_test() {
	if type -p git; then
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
	pushd $1 > /dev/null
	if branch=$(git symbolic-ref --short -q HEAD); then
	  default_remote=$(git config branch.${branch}.remote)
	else
	  vcs_terminate
	fi
	if [ $? -eq 0 ]; then
		git remote get-url ${default_remote}
	else
		vcs_terminate
	fi
	popd > /dev/null
}

vcs_terminate() {
	popd > /dev/null
	exit 1
}
