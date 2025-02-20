from typing import Dict, Optional, Set, Any
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
import pyparsing as pp
from collections import defaultdict

@dataclass
class ParserMetrics:
    """Stores metrics for a single parser."""
    total_time: float = 0.0
    calls: int = 0
    matches: int = 0
    max_time: float = 0.0
    min_time: float = float('inf')
    
    def add_measurement(self, duration: float, matched: bool) -> None:
        """Add a new measurement for this parser."""
        self.total_time += duration
        self.calls += 1
        if matched:
            self.matches += 1
        self.max_time = max(self.max_time, duration)
        self.min_time = min(self.min_time, duration)
    
    @property
    def avg_time(self) -> float:
        """Calculate average time per call."""
        return self.total_time / self.calls if self.calls > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate of the parser."""
        return self.matches / self.calls if self.calls > 0 else 0.0

class ParserProfiler:
    """Profiles pyparsing parsers performance."""
    
    def __init__(self):
        self.metrics: Dict[str, ParserMetrics] = defaultdict(ParserMetrics)
        self._original_methods = {}
        self._active = False
        self._instrumented: Set[int] = set()
    
    def _get_parser_name(self, parser: pp.ParserElement) -> str:
        """Get a meaningful name for the parser."""
        if parser.name:
            return parser.name
        # Try to get a more meaningful name for unnamed parsers
        if isinstance(parser, pp.Word):
            return f"Word({parser.initCharsOrig})"
        if isinstance(parser, pp.Literal):
            return f"Literal({parser.match})"
        if isinstance(parser, pp.OneOf):
            return f"OneOf({parser.strs})"
        return str(parser)
    
    def _wrap_method(self, parser: pp.ParserElement, method_name: str) -> None:
        """Wrap a parser method to collect metrics."""
        if (id(parser), method_name) in self._instrumented:
            return
            
        original_method = getattr(parser, method_name)
        self._original_methods[(id(parser), method_name)] = original_method
        parser_name = self._get_parser_name(parser)
        
        def wrapped_method(*args, **kwargs):
            if not self._active:
                return original_method(*args, **kwargs)
                
            start_time = time.perf_counter()
            try:
                result = original_method(*args, **kwargs)
                success = True
            except (pp.ParseException, IndexError):
                success = False
                raise
            finally:
                duration = time.perf_counter() - start_time
                self.metrics[parser_name].add_measurement(duration, success)
            
            return result
            
        setattr(parser, method_name, wrapped_method)
        self._instrumented.add((id(parser), method_name))
    
    def _wrap_parse_action(self, parser: pp.ParserElement) -> None:
        """Wrap parse actions to collect metrics."""
        if not parser.parseAction:
            return
            
        original_actions = parser.parseAction
        parser_name = f"{self._get_parser_name(parser)}_action"
        
        def wrapped_action(s, l, t):
            start_time = time.perf_counter()
            try:
                for action in original_actions:
                    t = action(s, l, t)
                success = True
            except Exception:
                success = False
                raise
            finally:
                duration = time.perf_counter() - start_time
                self.metrics[parser_name].add_measurement(duration, success)
            return t
            
        parser.parseAction = [wrapped_action]
    
    def instrument_parser(self, parser: pp.ParserElement) -> None:
        """Recursively instrument a parser and all its components."""
        # First wrap the main parser methods
        self._wrap_method(parser, 'parseImpl')
        self._wrap_method(parser, '_parseNoCache')
        self._wrap_parse_action(parser)
        
        # Then recursively wrap all child parsers
        seen = set()
        def _instrument_recursive(p):
            if id(p) in seen:
                return
            seen.add(id(p))
            
            self._wrap_method(p, 'parseImpl')
            self._wrap_method(p, '_parseNoCache')
            self._wrap_parse_action(p)
            
            for child in p.recurse():
                if id(child) not in seen:
                    _instrument_recursive(child)
        
        _instrument_recursive(parser)
    
    def reset(self) -> None:
        """Reset all collected metrics."""
        self.metrics.clear()
    
    @contextmanager
    def profile(self, parser: pp.ParserElement):
        """Context manager for profiling a parser."""
        self.instrument_parser(parser)
        self._active = True
        try:
            yield self
        finally:
            self._active = False
    
    def print_report(self, min_calls: int = 1, sort_by: str = 'total_time') -> None:
        """Print a performance report of all parsers."""
        valid_metrics = {
            name: m for name, m in self.metrics.items() 
            if m.calls >= min_calls
        }
        
        if not valid_metrics:
            print("No metrics collected.")
            return
            
        # Determine sorting key
        if sort_by == 'total_time':
            key_func = lambda x: x[1].total_time
        elif sort_by == 'avg_time':
            key_func = lambda x: x[1].avg_time
        elif sort_by == 'calls':
            key_func = lambda x: x[1].calls
        else:
            raise ValueError(f"Invalid sort_by value: {sort_by}")
            
        # Sort metrics
        sorted_metrics = sorted(
            valid_metrics.items(),
            key=key_func,
            reverse=True
        )
        
        # Print report
        print("\nParser Performance Report")
        print("-" * 100)
        print(f"{'Parser':<40} {'Calls':>8} {'Success%':>8} "
              f"{'Total(s)':>10} {'Avg(ms)':>10} {'Max(ms)':>10}")
        print("-" * 100)
        
        for name, metrics in sorted_metrics:
            print(f"{name[:40]:<40} {metrics.calls:>8} "
                  f"{metrics.success_rate*100:>7.1f}% "
                  f"{metrics.total_time:>10.3f} "
                  f"{metrics.avg_time*1000:>10.3f} "
                  f"{metrics.max_time*1000:>10.3f}")

def test_parser_profiler():
    """Test the ParserProfiler with a simple grammar."""
    # Create a simple grammar
    integer = pp.Word(pp.nums).setName("integer")
    identifier = pp.Word(pp.alphas).setName("identifier")
    operator = pp.oneOf("+ - * /").setName("operator")
    
    # Create an expression with nested components
    expr = pp.Forward().setName("expression")
    atom = (integer | identifier).setName("atom")
    
    # Add some parse actions to test action profiling
    def convert_integer(s, l, t):
        return int(t[0])
    
    integer.setParseAction(convert_integer)
    
    # Define the expression
    expr << (atom + pp.ZeroOrMore(operator + atom)).setName("full_expression")
    
    # Create test data
    test_input = "123 + abc * 456"
    
    # Create profiler
    profiler = ParserProfiler()
    
    # Profile parsing
    with profiler.profile(expr):
        result = expr.parseString(test_input)
        
    # Verify that metrics were collected
    assert len(profiler.metrics) > 0
    
    # Print report for visual inspection
    profiler.print_report()
    
    # Verify specific components were measured
    component_names = set(profiler.metrics.keys())
    print("\nCollected metrics for:", sorted(component_names))
    
    # Test reset
    profiler.reset()
    assert len(profiler.metrics) == 0

if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
