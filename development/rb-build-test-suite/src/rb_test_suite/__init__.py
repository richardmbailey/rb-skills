"""Candidate-bound test-suite contracts and deterministic acceptance policy."""
from .validation import ContractError, parse_json, parse_yaml, parse_xml, validate_record, validate_run
from .policy import evaluate_criterion, evaluate_gate, exit_code
__version__ = '0.1.0'
__all__ = ['ContractError', 'parse_json', 'parse_yaml', 'parse_xml', 'validate_record', 'validate_run',
           'evaluate_criterion', 'evaluate_gate', 'exit_code']
