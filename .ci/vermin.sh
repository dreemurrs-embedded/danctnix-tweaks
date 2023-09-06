#!/bin/sh -e
# Description: verify that we don't use too new python features
# https://postmarketos.org/pmb-ci

if [ "$(id -u)" = 0 ]; then
	set -x
	apk -q add vermin
	exec su "${TESTUSER:-build}" -c "sh -e $0"
fi

# shellcheck disable=SC2046
vermin \
	-t=3.7- \
	--backport argparse \
	--backport configparser \
	--backport enum \
	--backport importlib \
	--lint \
	--no-parse-comments \
	$(find . -name '*.py')
