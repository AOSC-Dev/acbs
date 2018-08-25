pm_whoprov(){
	dpkg-query -S $1 2> /dev/null | cut -d: -f 1
	# This just give a nice list of formatted dependencies.
}

pm_getver(){
	dpkg-query -f '${Version}' -W $1 2>/dev/null
}

pm_exists(){
	dpkg -l "$@" | grep ^ii &>/dev/null
}

pm_repoupdate(){
	apt update
}

pm_repoinstall(){
	apt install "$@" --yes
}

pm_repoquery(){
	apt show "$@"
}

pm_correction(){
	apt update
	apt install -f
}
