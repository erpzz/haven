#!/usr/bin/env python3
"""Independent negative controls against a supplied peer world.py. No inference.

This executes trusted peer source locally, never edits frozen files or scores a
real model. A false-positive verdict means the scorer accepted a crafted invalid
record; it does not establish that a student produced that record.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('world', type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('peer_world', args.world)
    world = importlib.util.module_from_spec(spec); spec.loader.exec_module(world)
    episode = world.make_episode('train', 'own_note', 0)
    call = episode['oracle']['calls'][0][0]
    record = {'ok_transport': True, 'format_errors': [], 'answer': episode['oracle']['answer'],
              'trace': [{**call, 'output': {'ok': False, 'error': 'NOT_FOUND_OR_NOT_AUTHORIZED'}}]}
    cases = {}
    cases['failed_tool_then_guessed_evidence'] = world.verify(episode, record)
    grounded = copy.deepcopy(record)
    grounded['trace'][0]['output'] = json.loads(world.dispatch(
        episode['world'], episode['principal'], call['name'], call['arguments']))
    cases['valid_grounded_positive_control'] = world.verify(episode, grounded)
    duplicate = copy.deepcopy(episode)
    duplicate['check']['required'] *= 2
    duplicate['check']['ordered'] = False
    cases['one_trace_satisfies_two_distinct_requirements'] = world.verify(duplicate, grounded)
    negated = copy.deepcopy(grounded)
    negated['answer'] = 'The following statement is false: ' + negated['answer']
    cases['negated_answer_contains_expected_substrings'] = world.verify(episode, negated)
    print(json.dumps({'classification': 'STATIC_TEST', 'source_sha256': hashlib.sha256(args.world.read_bytes()).hexdigest(),
                      'crafted_records': {name: {'accepted': result['pass'], 'expected_accept': name == 'valid_grounded_positive_control', 'verdict': result}
                                                   for name, result in cases.items()},
                      'limits': 'No model run. These are scorer falsification tests, not observed model exploits.'}, indent=2))


if __name__ == '__main__': main()
