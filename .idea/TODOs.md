### Multiple source format?

- Arch `PKGBUILD` like spec:

  This is Bash compatible
  
  Breaks compatiblity with `abbs`
  ```bash
  SRCTBL=('url1', 'url2')
  ```

- Simple form:

  This is Bash compatible

  Breaks compatiblity with `abbs`
  ```bash
  SRCTBL='url1 url2'
  ```


### Check sum format?

- Arch `PKGBUILD` like spec:

  This is Bash compatible
  ```bash
  # Matching: Regular Bash expression
  md5sum=('d41d8cd98f00b204e9800998ecf8427e')
  ```

- Simple layout

  This is Bash compatible
  ```bash
  # Matching: Regular Bash expression
  MD5SUM='d41d8cd98f00b204e9800998ecf8427e'
  ```

- BSD tag like spec:

  This is **not** Bash compatible
  ```python
  # Matching: RegExp:
  match = r'(\w+).*?\((.*?)\).*?\=(.*)'
  # Example:
  MD5SUM(file)='d41d8cd98f00b204e9800998ecf8427e'
  ```
- Mixed:

  This seems to be Bash compatible
  ```bash
  # Example:
  CHKSUM='md5::d41d8cd98f00b204e9800998ecf8427e'
  # Example 2:
  CHKSUM='md5(d41d8cd98f00b204e9800998ecf8427e)'
  ```
