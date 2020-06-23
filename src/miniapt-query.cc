#include <apt-pkg/cachefile.h>
#include <apt-pkg/pkgcache.h>
#include <apt-pkg/policy.h>
#include <apt-pkg/cachefile.h>
#include <apt-pkg/cacheset.h>

#include "miniapt-query.h"

static pkgPolicy *policy;
static pkgCache *cache;
static pkgDepCache *depCache;

bool apt_init_system()
{
    return pkgInitConfig(*_config) && pkgInitSystem(*_config, _system);
}

int check_available(const char *name)
{
    pkgCacheFile cachefile;
    pkgDepCache *depCache = cachefile.GetDepCache();
    if (!depCache)
        return -1;
    cache = cachefile.GetPkgCache();
    if (!cache)
        return -2;
    policy = cachefile.GetPolicy();
    if (!policy)
        return -3;

    APT::CacheSetHelper helper(true, GlobalError::NOTICE);
    APT::PackageList pkgset = APT::PackageList::FromCommandLine(cachefile, &name, helper);
    for (APT::PackageList::const_iterator Pkg = pkgset.begin(); Pkg != pkgset.end(); ++Pkg)
    {
        if (depCache->GetCandidateVersion(Pkg)) return 1;
    }
    return 0;
}
