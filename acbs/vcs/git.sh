# notice: on error, an error code should be returned by `exit` or `return`
# - return value: print to std output in utf-8
# creating new functions is allowed, but don't delete necessary ones.

# vcs_repofetch: accepts 3 args: 1. URL 2. dest folder 3. depth
# - return plain URL
#
vcs_repofetch() {
	# always do it fast; and do 4 submodules at once
	git clone --recurse-submodules --shallow-submodules -j4 --depth ${3:1} $1 $2
	# but also always keep the refs (we could also do --no-single-branch but some repos are still huge with it)
	git config 'remote.origin.fetch' '+refs/heads/*:refs/remotes/origin/*'
}

# vcs_switchbranch: accepts 1 arg: 1. new branch
vcs_switchbranch() {
	# it could be shallow, so let's fetch it first
	git fetch --recurse-submodules --update-shallow -j4 origin $1
	git checkout $1
}

# vcs_switchcommit: accepts 1 arg: 1. commit hash
vcs_switchcommit() {
	vcs_switchbranch "$@"
}

# vcs_repoupdate: accepts 1 arg: 1. new URL
# - return nothing
# - remark - you may want to check if conflicts exist
vcs_repoupdate() {
	git pull --recurse-submodules --update-shallow -j4 $1
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
