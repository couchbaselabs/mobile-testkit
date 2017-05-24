#!/usr/bin/env bash

echo "Removing all untracked files ..."
# -ff - required to delete untracked files and directories, the second f will remove
#   untracked directories with a .git subfolder (i.e. removed submodules)
# -d - required to remove untracked directories
# -x - remove .gitignore ignored files as well
git clean -ffdx