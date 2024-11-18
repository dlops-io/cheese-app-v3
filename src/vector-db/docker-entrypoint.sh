#!/bin/bash

echo "Container is running!!!"

# args="$@"
# echo $args

# if [[ -z ${args} ]]; 
# then
#     pipenv shell
# else
#   pipenv run python $args
# fi

if [ "${DEV}" = 1 ]; then
  pipenv shell
else
  pipenv run python cli.py --download --load --chunk_type recursive-split
fi