# Contributing

GRR is a somewhat complex piece of code. While this complexity is necessary to provide the scale and performance characteristics we need, it makes it more difficult to get involved and understand the code base. So just be aware that making significant changes in the core will be difficult if you don't have a software engineering background, or solid experience with python that includes use of things like pdb and profiling.

That said, we want your contribution! you don't need to be a veteran pythonista to contribute artifacts or parsers. But whatever your experience, we strongly recommend starting somewhere simple before embarking on core changes and reading our documentation. 

In particular we recommend:
* Build a standalone console script to perform the actions you want. A standalone console script won't benefit from being able to be run as a Collector or a Hunt, but it will get you familiar with the API, and an experienced developer can convert it into a fully fledged flow afterwards.
* Add to Artifacts or an existing flow. Many flows could do with work to detect more things or support additional platforms such as the Autoruns or Registry parsing flow.
* Add a new parser to parse a new filetype, e.g. if you have a different Anti-virus or HIDS log you want to parse.

Additionally if you have big ideas, it is definitely worth bouncing them off the core development team early on the developers list. They may already be underway, conflict with something else, or have a much simpler solution. Get that feedback before you start coding.

## If you find a security vulnerability:

1. **DO NOT POST ABOUT IT PUBLICLY**
2. Send an email to sroberts@github.com with details about the security vulnerability.
3. After a fix has been released, a public announcement will be made giving all glory and honor to you.

## If you find what looks like a bug:

1. Search the [developers mailing list](https://groups.google.com/forum/#!forum/grr-dev) to see if anyone else had the same issue.
2. Check the [GitHub issue tracker](https://github.com/grr-hackers/grr/issues) to see if anyone else has reported issue.
3. If you don't see anything, [create an issue](https://github.com/grr-hackers/grr/issues/new) with information on how to reproduce the issue.

## If you want to contribute an enhancement or a fix:

1. Fork the project on GitHub.
1. Commit the changes.
1. Send a pull request.
