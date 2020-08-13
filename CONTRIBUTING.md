# Contributing to Tortoise bot

We would love your input! This open source repository is open to new ideas and improvements from anyone.

When contributing to this repository, please first discuss the change you wish to make via issues or via chat in our Discord server.

Note that contributions may not be accepted immediately on the basis of a contributor failing to follow these guidelines.

## Your code changes should happen through pull requests

We actively welcome your pull requests:

1. Fork the repo and create new branch from `dev` in your fork. Name the branch appropriately eg. `feature-music-playlist` or `bugfix-countdown-command`.
2. Your code should follow our [Code Rules](#code-rules)
3. Issue that pull request! You should target our `dev` branch and your base would be your branch from your fork.

When PR is opened **ensure that "Allow edits from maintainers" is checked**. This gives permission for maintainers to commit changes directly to your fork, if necessary, thus speeding up the review process.

## Code Rules

Use a Consistent Coding Style

1. **No force-pushes** or modifying the Git history in any way.
2. Do not push directly to `master` branch, only push to `dev`
    * If PRing from your own fork, **ensure that "Allow edits from maintainers" is checked**. This gives permission for maintainers to commit changes directly to your fork, speeding up the review process.
3. **Adhere to the prevailing code style**, which we enforce using [`flake8`](http://flake8.pycqa.org/en/latest/index.html) and [`pre-commit`](https://pre-commit.com/).
    * Run `flake8` and `pre-commit` against your code **before** you push it.
    If you followed instructions in our README #Installation-Instructions for DEV you should have a working linter and pre-commit already setup.
    
    Some minor things you might notice:
    - Codebase uses double quotes `"` for strings.
    - Imports are sorted by length, top to bottom from built-in, installed and project modules.

4. Try not to break basic programming principles, for example DRY or bad variable names, for example:
   - Try to use our `cogs/utils` for your code. If you have something new then edit those utils. 
   For example have a new specific embed? Add it in embed_handler.
   
   - Don't have variable names such as `i`, `a` etc we prefer descriptive names even if they might be longer.
    
5. **Make great commits**. A well structured git log is key to a project's maintainability; it efficiently provides insight into when and *why* things were done for future maintainers of the project.
    * Commits should be as narrow in scope as possible. Commits that span hundreds of lines across multiple unrelated functions and/or files are very hard for maintainers to follow. After about a week they'll probably be hard for you to follow too.

## Any contributions you make will be under the MIT Software License
In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project.

## Report bugs using Github's issues
We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/Tortoise-Community/Tortoise-BOT/issues)

## Write bug reports with detail, background, and code in question

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People *love* thorough bug reports. I'm not even kidding.

## Write issues with detail

Have a new idea? Want to discuss existing one?

When opening issue for discussion make sure you go into details and give as much info as you can.

For example:
- A quick summary (what's it for, what would it do)
- Reason for having this
- Approximate things that would need to be added/changed (if lot make a todo list)
- Possibly some short example code

## License
By contributing, you agree that your contributions will be licensed under its MIT License.

## Changes to this Arrangement

All projects evolve over time, and this contribution guide is no different. This document is open to pull requests or changes by contributors. If you believe you have something valuable to add or change, please don't hesitate to do so in a PR.

##  Supplemental Information
### Developer Environment
Instructions for setting the bot developer environment can be found in the [README.md](https://github.com/Tortoise-Community/Tortoise-BOT) of our repo under #Installation-Instructions

### Type Hinting
[PEP 484](https://www.python.org/dev/peps/pep-0484/) formally specifies type hints for Python functions, added to the Python Standard Library in version 3.5. Type hints are recognized by most modern code editing tools and provide useful insight into both the input and output types of a function, preventing the user from having to go through the codebase to determine these types.

For example:

```py
from typing import Dict


def foo(input_1: int, input_2: Dict[str, int]) -> bool:
    ...
```

Tells us that `foo` accepts an `int` and a `Dict`, which is a dictionary where keys are strings and values ints, and returns a `bool`.

All function declarations should be type hinted in contributed code.

For more information, see *[PEP 483](https://www.python.org/dev/peps/pep-0483/) - The Theory of Type Hints* and Python's documentation for the [`typing`](https://docs.python.org/3/library/typing.html) module.

### Logging Levels
The project currently defines [`logging`](https://docs.python.org/3/library/logging.html) levels as follows, from lowest to highest severity:
* **DEBUG:** These events should add context to what's happening in a development setup to make it easier to follow what's going while working on a project.
* **INFO:** These events are normal and don't need direct attention but are worth keeping track of in production, like checking which cogs were loaded during a start-up.
* **WARNING:** These events are out of the ordinary and should be fixed, but have not caused a failure.
* **ERROR:** These events have caused a failure in a specific part of the application and require urgent attention.
* **CRITICAL:** These events have caused the whole application to fail (or big part of it) and require immediate intervention.

*Note* you should not use `print` but instead you should use logger eg. `logger.info("Something started")`

## Footnotes

This file was inspired by:

- https://github.com/python-discord/bot
- https://github.com/junosuarez/CONTRIBUTING.md
- https://gist.github.com/briandk/3d2e8b3ec8daf5a27a62
- https://gist.github.com/PurpleBooth/b24679402957c63ec426