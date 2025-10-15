import re
import json
from typing import Dict, Any, List

def get_default_code_template(language: str, problem_title: str = "") -> str:
    """Get default code template for a language without backend logic"""
    
    templates = {
        'python3': '''# Write your solution here
def solution():
    pass

# Example usage:
# result = solution()
# print(result)
''',
        
        'cpp17': '''#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
using namespace std;

int main() {
    // Write your solution here
    
    return 0;
}
''',
        
        'java': '''import java.util.*;
import java.io.*;

public class Main {
    public static void main(String[] args) {
        // Write your solution here
        
    }
}
''',
        
        'javascript': '''// Write your solution here
function solution() {
    
}

// Example usage:
// console.log(solution());
''',
        
        'csharp': '''using System;
using System.Collections.Generic;

class Program {
    static void Main() {
        // Write your solution here
        
    }
}
''',
        
        'go': '''package main

import (
    "fmt"
)

func main() {
    // Write your solution here
    
}
''',
        
        'rust': '''fn main() {
    // Write your solution here
    
}
''',
        
        'php': '''<?php
// Write your solution here

?>
''',
        
        'ruby': '''# Write your solution here
def solution
    
end

# Example usage:
# puts solution()
''',
        
        'kotlin': '''fun main() {
    // Write your solution here
    
}
''',
        
        'swift': '''import Foundation

// Write your solution here

'''
    }
    
    return templates.get(language, "// Write your solution here")

def analyze_time_complexity(code: str, language: str) -> str:
    """Basic time complexity analysis based on code patterns"""
    code_lower = code.lower()
    
    # Common patterns across languages
    nested_loop_patterns = [
        r'for.*for', r'while.*while', r'for.*while', r'while.*for'
    ]
    
    single_loop_patterns = [
        r'for\s*\(', r'while\s*\(', r'for\s+\w+\s+in', r'forEach'
    ]
    
    sort_patterns = [
        r'sort\s*\(', r'sorted\s*\(', r'\.sort\s*\(', r'Arrays\.sort',
        r'Collections\.sort', r'std::sort', r'sort\.Slice'
    ]
    
    hash_patterns = [
        r'dict\s*\(', r'set\s*\(', r'HashMap', r'HashSet', r'unordered_map',
        r'unordered_set', r'Map\s*\(', r'Set\s*\('
    ]
    
    # Count nested loops
    nested_count = 0
    for pattern in nested_loop_patterns:
        nested_count += len(re.findall(pattern, code_lower, re.DOTALL))
    
    if nested_count >= 2:
        return "O(n³)"
    elif nested_count >= 1:
        return "O(n²)"
    
    # Check for single loops
    loop_count = 0
    for pattern in single_loop_patterns:
        loop_count += len(re.findall(pattern, code_lower))
    
    # Check for sorting
    sort_count = 0
    for pattern in sort_patterns:
        sort_count += len(re.findall(pattern, code_lower))
    
    # Check for hash operations
    hash_count = 0
    for pattern in hash_patterns:
        hash_count += len(re.findall(pattern, code_lower))
    
    if sort_count > 0:
        return "O(n log n)"
    elif loop_count > 0:
        return "O(n)"
    elif hash_count > 0:
        return "O(1) average"
    
    return "O(1)"

def analyze_space_complexity(code: str, language: str) -> str:
    """Basic space complexity analysis"""
    code_lower = code.lower()
    
    # Patterns that indicate space usage
    array_patterns = [
        r'list\s*\(', r'array\s*\(', r'vector\s*<', r'ArrayList',
        r'\[\]', r'Array\s*\('
    ]
    
    hash_patterns = [
        r'dict\s*\(', r'set\s*\(', r'HashMap', r'HashSet', r'unordered_map',
        r'unordered_set', r'Map\s*\(', r'Set\s*\('
    ]
    
    # Check for data structures
    array_count = 0
    for pattern in array_patterns:
        array_count += len(re.findall(pattern, code_lower))
    
    hash_count = 0
    for pattern in hash_patterns:
        hash_count += len(re.findall(pattern, code_lower))
    
    if array_count > 0 or hash_count > 0:
        return "O(n)"
    
    return "O(1)"

def validate_test_case_data(input_data: str, expected_output: str) -> Dict[str, Any]:
    """Validate and normalize test case data"""
    errors = []
    warnings = []
    
    # Clean whitespace
    input_data = input_data.strip()
    expected_output = expected_output.strip()
    
    # Basic validation
    if not input_data and not expected_output:
        errors.append("Both input and expected output cannot be empty")
    
    # Check for common issues
    if '\r\n' in input_data or '\r\n' in expected_output:
        warnings.append("Windows line endings detected, converting to Unix format")
        input_data = input_data.replace('\r\n', '\n')
        expected_output = expected_output.replace('\r\n', '\n')
    
    # Check for trailing whitespace
    if input_data.endswith(' ') or input_data.endswith('\t'):
        warnings.append("Trailing whitespace in input data")
    
    if expected_output.endswith(' ') or expected_output.endswith('\t'):
        warnings.append("Trailing whitespace in expected output")
    
    return {
        'input_data': input_data,
        'expected_output': expected_output,
        'errors': errors,
        'warnings': warnings,
        'is_valid': len(errors) == 0
    }

def format_execution_time(seconds: float) -> str:
    """Format execution time in human readable format"""
    if seconds < 0.001:
        return f"{seconds * 1000:.1f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    else:
        return f"{seconds:.3f}s"

def format_memory_usage(bytes_used: float) -> str:
    """Format memory usage in human readable format"""
    if bytes_used < 1024:
        return f"{bytes_used:.1f}B"
    elif bytes_used < 1024 * 1024:
        return f"{bytes_used / 1024:.1f}KB"
    else:
        return f"{bytes_used / (1024 * 1024):.1f}MB"

def sanitize_code_output(output: str, max_length: int = 10000) -> str:
    """Sanitize and truncate code output"""
    if not output:
        return ""
    
    # Remove null bytes and other control characters
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', output)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "\n... (output truncated)"
    
    return sanitized

def parse_compiler_error(error_message: str, language: str) -> Dict[str, Any]:
    """Parse compiler error messages to extract useful information"""
    parsed = {
        'type': 'compilation_error',
        'line': None,
        'column': None,
        'message': error_message,
        'suggestions': []
    }
    
    # Language-specific parsing
    if language == 'python3':
        # Python syntax errors
        if 'SyntaxError' in error_message:
            parsed['type'] = 'syntax_error'
            # Extract line number
            line_match = re.search(r'line (\d+)', error_message)
            if line_match:
                parsed['line'] = int(line_match.group(1))
        elif 'IndentationError' in error_message:
            parsed['type'] = 'indentation_error'
            parsed['suggestions'].append('Check your indentation')
    
    elif language in ['cpp17', 'csharp']:
        # C++ / C# compilation errors
        error_match = re.search(r'error:?\s*(.+)', error_message, re.IGNORECASE)
        if error_match:
            parsed['message'] = error_match.group(1)
    
    elif language == 'java':
        # Java compilation errors
        if 'cannot find symbol' in error_message.lower():
            parsed['suggestions'].append('Check variable/method names and imports')
        elif 'expected' in error_message.lower():
            parsed['suggestions'].append('Check syntax and missing semicolons')
    
    return parsed

def calculate_problem_difficulty_score(problem) -> float:
    """Calculate a numerical difficulty score for a problem"""
    base_scores = {
        'EASY': 100,
        'MEDIUM': 200,
        'HARD': 300
    }
    
    score = base_scores.get(problem.difficulty, 100)
    
    # Adjust based on acceptance rate
    if problem.acceptance_rate > 0:
        if problem.acceptance_rate < 30:
            score += 50
        elif problem.acceptance_rate < 50:
            score += 25
        elif problem.acceptance_rate > 80:
            score -= 25
    
    # Adjust based on number of test cases
    test_case_count = problem.test_cases.count()
    if test_case_count > 10:
        score += 20
    elif test_case_count < 5:
        score -= 10
    
    return max(50, score)  # Minimum score of 50

def generate_problem_hints(problem_statement: str, difficulty: str) -> List[str]:
    """Generate automatic hints based on problem content"""
    hints = []
    statement_lower = problem_statement.lower()
    
    # Common algorithmic patterns
    if any(word in statement_lower for word in ['array', 'list', 'sequence']):
        hints.append("Consider different ways to iterate through the array")
    
    if any(word in statement_lower for word in ['sort', 'order', 'arrange']):
        hints.append("Think about sorting algorithms or maintaining sorted order")
    
    if any(word in statement_lower for word in ['find', 'search', 'locate']):
        hints.append("Consider binary search if the data is sorted")
    
    if any(word in statement_lower for word in ['duplicate', 'unique', 'distinct']):
        hints.append("Hash tables can help track seen elements efficiently")
    
    if any(word in statement_lower for word in ['path', 'route', 'traverse']):
        hints.append("This might be a graph traversal problem (BFS/DFS)")
    
    if any(word in statement_lower for word in ['maximum', 'minimum', 'optimal']):
        hints.append("Dynamic programming might be useful here")
    
    # Difficulty-specific hints
    if difficulty == 'HARD':
        hints.append("Break down the problem into smaller subproblems")
        hints.append("Consider the time and space complexity of your solution")
    
    return hints[:3]  # Limit to 3 hints

def validate_problem_constraints(constraints: str) -> Dict[str, Any]:
    """Validate and parse problem constraints"""
    result = {
        'is_valid': True,
        'parsed_constraints': [],
        'warnings': [],
        'errors': []
    }
    
    if not constraints.strip():
        result['warnings'].append("No constraints specified")
        return result
    
    # Parse constraint patterns
    constraint_patterns = [
        r'(\d+)\s*≤\s*(\w+)\s*≤\s*(\d+)',  # 1 ≤ n ≤ 1000
        r'(\d+)\s*<=\s*(\w+)\s*<=\s*(\d+)',  # 1 <= n <= 1000
        r'(\w+)\s*∈\s*\[(\d+),\s*(\d+)\]',   # n ∈ [1, 1000]
    ]
    
    for line in constraints.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        parsed = False
        for pattern in constraint_patterns:
            match = re.search(pattern, line)
            if match:
                result['parsed_constraints'].append({
                    'variable': match.group(2) if len(match.groups()) >= 2 else 'unknown',
                    'min_value': match.group(1),
                    'max_value': match.group(3) if len(match.groups()) >= 3 else match.group(1),
                    'original': line
                })
                parsed = True
                break
        
        if not parsed:
            result['warnings'].append(f"Could not parse constraint: {line}")
    
    return result