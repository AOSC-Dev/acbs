This is the doumentation part.

## Updating

Just run:
```bash
make dirhtml
pushd build/dirhtml
git commit -am 'Update doc'
git push
popd
```

## Explanation

Due to human laziness we have opted to put the gh-pages branch as a submodule
in here. It works fine.

