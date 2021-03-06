# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from os import getcwd
import re
from sys import argv, exit, stderr, stdout

from fabric.network import disconnect_all

from ..exceptions import NoSuchRepository
from ..repo import Repository
from ..utils.text import mark_for_translation as _, red
from .parser import build_parser_bw

ANSI_ESCAPE = re.compile(r'\x1b[^m]*m')


class FilteringHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            stream = stderr
        else:
            stream = stdout

        try:
            msg = self.format(record)

            if stream.isatty():
                stream.write(msg)
            else:
                stream.write(ANSI_ESCAPE.sub("", msg).encode('UTF-8'))
            stream.write("\n")

            self.acquire()
            try:
                stream.flush()
            finally:
                self.release()
        except:
            self.handleError(record)


def set_up_logging(debug=False, interactive=False):
    if debug:
        format = "%(asctime)s [%(levelname)s:%(name)s:%(process)d] %(message)s"
        level = logging.DEBUG
    elif interactive:
        format = "%(message)s"
        level = logging.ERROR
    else:
        format = "%(message)s"
        level = logging.INFO

    formatter = logging.Formatter(format)

    handler = FilteringHandler()
    handler.setFormatter(formatter)
    handler.setLevel(level)

    logger = logging.getLogger('blockwart')
    logger.addHandler(handler)
    logger.setLevel(level)

    logging.getLogger('paramiko').setLevel(logging.ERROR)
    logging.getLogger('passlib').setLevel(logging.ERROR)


def main(*args):
    """
    Entry point for the 'bw' command line utility.

    args:   used for integration tests
    """
    if not args:
        args = argv[1:]

    if len(args) >= 1 and (
        args[0] == "--version" or
        (args[0] == "repo" and args[1] == "create") or
        args[0] == "zen" or
        "-h" in args or
        "--help" in args
    ):
        # 'bw repo create' is a special case that only takes a path
        repo = getcwd()
    else:
        try:
            repo = Repository(getcwd())
        except NoSuchRepository:
            print(_("{x} The current working directory "
                    "is not a Blockwart repository.".format(x=red("!"))))
            exit(1)

    parser_bw = build_parser_bw()
    args = parser_bw.parse_args(args)

    try:
        interactive = args.interactive
    except AttributeError:
        interactive = False

    set_up_logging(
        debug=args.debug,
        interactive=interactive,
    )

    output = args.func(repo, args)
    if output is None:
        output = ()

    for line in output:
        print(line.encode('utf-8'))

    # clean up Fabric connections
    disconnect_all()
