"""
Engineering Practices Evaluator Tool Implementation for ADK Code Review System.

This tool evaluates software engineering best practices, SOLID principles, and development workflows.
"""

import time
import re
from typing import Dict, Any, List, Optional

from google.adk.tools.tool_context import ToolContext


def evaluate_engineering_practices(tool_context: ToolContext, code: str = "") -> Dict[str, Any]:
    """
    Evaluate engineering practices and software development best practices.
    
    Args:
        tool_context: ADK ToolContext containing session state and parameters
        code: Optional code override (fallback). Prefer tool_context.state["code"].
        
    Returns:
        dict: Engineering practices evaluation results with actual file paths and code evidence
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info("🔧 [evaluate_engineering_practices] Tool called")
    
    execution_start = time.time()
    
    try:
        # Get code from tool context (prefer state over parameter)
        code_from_state = tool_context.state.get('code', '')
        code = code_from_state or code or ''
        files = tool_context.state.get('files', [])  # File metadata
        language = tool_context.state.get('language', 'python')
        file_path = tool_context.state.get('file_path', 'unknown')
        
        logger.info(f"🔧 [evaluate_engineering_practices] code length: {len(code)}, files count: {len(files)}")
        
        if not code:
            logger.error("❌ [evaluate_engineering_practices] No code provided")
            return {
                'status': 'error',
                'error_message': 'No code provided for engineering practices evaluation',
                'tool_name': 'evaluate_engineering_practices'
            }
        
        # Parse combined code into individual files
        logger.info("🔧 [evaluate_engineering_practices] Parsing combined code...")
        parsed_files = _parse_combined_code(code)
        logger.info(f"🔧 [evaluate_engineering_practices] Parsed {len(parsed_files)} files")
        
        # If parsing fails, use files metadata
        if not parsed_files and files:
            logger.warning("⚠️  [evaluate_engineering_practices] Parsing failed, using files metadata")
            parsed_files = []
            for file_info in files:
                parsed_files.append({
                    'file_path': file_info.get('file_path', 'unknown'),
                    'language': file_info.get('language', 'unknown'),
                    'content': '',  # Content already consumed
                    'lines': file_info.get('lines', 0)
                })
        
        if not parsed_files:
            logger.error("❌ [evaluate_engineering_practices] Unable to parse files")
            return {
                'status': 'error',
                'error_message': 'Unable to parse files from combined code',
                'tool_name': 'evaluate_engineering_practices'
            }
        if not parsed_files:
            return {
                'status': 'error',
                'error_message': 'Unable to parse files from combined code',
                'tool_name': 'evaluate_engineering_practices'
            }
        
        # Analyze each file and collect findings with actual file paths
        all_findings = []
        file_scores = {}
        
        logger.info(f"🔧 [evaluate_engineering_practices] Analyzing {len(parsed_files)} files...")
        
        for file_data in parsed_files:
            file_path_actual = file_data['file_path']
            file_content = file_data['content']
            file_lang = file_data['language']
            
            logger.info(f"🔍 [evaluate_engineering_practices] Analyzing: {file_path_actual} ({file_lang}, {len(file_content)} chars)")
            
            # Skip empty files
            if not file_content or len(file_content.strip()) < 10:
                logger.warning(f"⚠️  [evaluate_engineering_practices] Skipping {file_path_actual} - empty or too short")
                continue
            
            # Analyze this specific file
            findings = _analyze_file_engineering_practices(
                file_content, 
                file_lang, 
                file_path_actual
            )
            
            logger.info(f"✅ [evaluate_engineering_practices] Found {len(findings)} issues in {file_path_actual}")
            
            # Add findings with actual file context
            if findings:
                all_findings.extend(findings)
            
            # Store per-file metrics
            file_scores[file_path_actual] = {
                'language': file_lang,
                'lines': len(file_content.split('\n')),
                'issue_count': len(findings)
            }
        
        logger.info(f"✅ [evaluate_engineering_practices] Total findings: {len(all_findings)} across {len(file_scores)} files")
        
        # Build comprehensive result with actual file evidence
        practices_result = {
            'status': 'success',
            'tool_name': 'evaluate_engineering_practices',
            'analysis_type': 'engineering_practices_evaluation',
            'files_analyzed': list(file_scores.keys()),
            'file_count': len(file_scores),
            'findings': all_findings,  # Each finding has file_path, line_number, code_snippet
            'file_scores': file_scores,
            'summary': {
                'total_findings': len(all_findings),
                'critical': sum(1 for f in all_findings if f.get('severity') == 'critical'),
                'high': sum(1 for f in all_findings if f.get('severity') == 'high'),
                'medium': sum(1 for f in all_findings if f.get('severity') == 'medium'),
                'low': sum(1 for f in all_findings if f.get('severity') == 'low')
            },
            'timestamp': time.time()
        }
        
        execution_time = time.time() - execution_start
        practices_result['execution_time_seconds'] = execution_time
        
        logger.info(f"✅ [evaluate_engineering_practices] Complete - {len(all_findings)} findings in {execution_time:.2f}s")
        
        return practices_result
        
    except Exception as e:
        execution_time = time.time() - execution_start
        error_result = {
            'status': 'error',
            'tool_name': 'evaluate_engineering_practices',
            'error_message': str(e),
            'error_type': type(e).__name__,
            'execution_time_seconds': execution_time
        }
        
        return error_result


def _parse_combined_code(combined_code: str) -> List[Dict[str, Any]]:
    """
    Parse combined code (with file headers) into individual files.
    
    Expected format:
    ================================================================================
    File: path/to/file.py
    Language: python
    Status: modified
    Lines: 123
    ================================================================================
    
    <file content>
    
    Returns:
        List of dicts with file_path, language, content, lines
    """
    import logging
    logger = logging.getLogger(__name__)
    
    files = []
    
    # Find all file header blocks
    # Pattern: ===\nFile: ...\nLanguage: ...\n...\n===\n<content>
    pattern = r'={80,}\n(File:.*?\n(?:Language:.*?\n)?(?:Status:.*?\n)?(?:Lines:.*?\n)?)={80,}\n(.*?)(?=\n={80,}|$)'
    
    matches = re.findall(pattern, combined_code, re.DOTALL)
    logger.info(f"🔧 [_parse_combined_code] Found {len(matches)} file blocks")
    
    for header, content in matches:
        file_info = {}
        
        # Parse header lines
        for line in header.strip().split('\n'):
            if line.startswith('File:'):
                file_info['file_path'] = line.replace('File:', '').strip()
            elif line.startswith('Language:'):
                file_info['language'] = line.replace('Language:', '').strip()
            elif line.startswith('Status:'):
                file_info['status'] = line.replace('Status:', '').strip()
            elif line.startswith('Lines:'):
                try:
                    file_info['lines'] = int(line.replace('Lines:', '').strip())
                except ValueError:
                    file_info['lines'] = 0
        
        file_info['content'] = content.strip()
        
        if file_info.get('file_path'):
            logger.info(f"✅ [_parse_combined_code] Parsed: {file_info['file_path']} ({file_info.get('language', 'unknown')}, {len(file_info['content'])} chars)")
            files.append(file_info)
        else:
            logger.warning(f"⚠️  [_parse_combined_code] Skipping block - no file path found")
    
    return files


def _analyze_file_engineering_practices(
    code: str, 
    language: str, 
    file_path: str
) -> List[Dict[str, Any]]:
    """
    Analyze a single file for engineering practice violations.
    Returns list of findings with actual file context.
    """
    findings = []
    
    # Extract functions and classes with line numbers
    functions = _extract_functions_with_lines(code, language)
    classes = _extract_classes_with_lines(code, language)
    
    # Check for long functions (SRP violation)
    for func in functions:
        if func['line_count'] > 50:
            findings.append({
                'type': 'long_function',
                'severity': 'high' if func['line_count'] > 80 else 'medium',
                'title': f"Long function: `{func['name']}`",
                'file_path': file_path,
                'line_start': func.get('line_start', 0),
                'line_end': func.get('line_end', 0),
                'code_snippet': func.get('snippet', ''),
                'description': f"Function has {func['line_count']} lines (threshold: 50). Long functions are harder to test and maintain.",
                'recommendation': f"Break down `{func['name']}` into smaller, focused functions with single responsibilities.",
                'confidence': 0.95
            })
    
    # Check for god classes
    for cls in classes:
        method_count = len(cls.get('methods', []))
        line_count = cls.get('line_count', 0)
        
        if method_count > 10 or line_count > 200:
            findings.append({
                'type': 'god_class',
                'severity': 'critical' if method_count > 15 else 'high',
                'title': f"God class anti-pattern: `{cls['name']}`",
                'file_path': file_path,
                'line_start': cls.get('line_start', 0),
                'line_end': cls.get('line_end', 0),
                'code_snippet': cls.get('snippet', ''),
                'description': f"Class has {method_count} methods and {line_count} lines. This violates Single Responsibility Principle.",
                'recommendation': f"Refactor `{cls['name']}` into smaller, focused services or modules.",
                'confidence': 0.90
            })
    
    # Check for missing error handling
    try_blocks = len(re.findall(r'\btry\s*:', code))
    except_blocks = len(re.findall(r'\bexcept\s+', code))
    
    if try_blocks > 0 and except_blocks == 0:
        findings.append({
            'type': 'missing_error_handling',
            'severity': 'medium',
            'title': 'Incomplete error handling',
            'file_path': file_path,
            'line_start': 0,
            'line_end': 0,
            'code_snippet': '',
            'description': f"Found {try_blocks} try blocks but no except blocks. Errors may not be handled properly.",
            'recommendation': 'Add appropriate except blocks to handle exceptions gracefully.',
            'confidence': 0.75
        })
    
    # Check for missing docstrings (Python/TypeScript)
    if language in ['python', 'typescript', 'javascript']:
        docstring_coverage = _assess_docstring_coverage_simple(code, language)
        if docstring_coverage < 30:
            findings.append({
                'type': 'poor_documentation',
                'severity': 'low',
                'title': 'Low docstring coverage',
                'file_path': file_path,
                'line_start': 0,
                'line_end': 0,
                'code_snippet': '',
                'description': f"Only {docstring_coverage}% of functions have docstrings. This reduces code maintainability.",
                'recommendation': 'Add docstrings to public functions and classes explaining their purpose, parameters, and return values.',
                'confidence': 0.80
            })
    
    return findings


def _extract_functions_with_lines(code: str, language: str) -> List[Dict[str, Any]]:
    """Extract functions with line numbers and snippets for multiple languages."""
    functions = []
    lines = code.split('\n')
    
    if language == 'python':
        # Match Python function definitions
        for i, line in enumerate(lines, 1):
            match = re.match(r'^(\s*)def\s+(\w+)\s*\(', line)
            if match:
                indent = len(match.group(1))
                func_name = match.group(2)
                
                # Find function end (next function or class at same/lower indent)
                end_line = i
                for j in range(i, len(lines)):
                    next_line = lines[j]
                    if next_line.strip() and not next_line.strip().startswith('#'):
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent <= indent and j > i:
                            if re.match(r'^\s*(def|class)\s+', next_line):
                                end_line = j
                                break
                else:
                    end_line = len(lines)
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+9, end_line)])  # First 10 lines
                
                functions.append({
                    'name': func_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'snippet': snippet
                })
    
    elif language in ['typescript', 'javascript']:
        # Match TS/JS function definitions
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(export\s+)?(async\s+)?(function|const|let|var)\s+(\w+)\s*[=\(]', line)
            if match:
                func_name = match.group(4)
                
                # Simple heuristic: count until closing brace
                brace_count = line.count('{') - line.count('}')
                end_line = i
                
                for j in range(i, min(i + 200, len(lines))):
                    next_line = lines[j]
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+9, end_line)])
                
                functions.append({
                    'name': func_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'snippet': snippet
                })
    
    elif language == 'java':
        # Match Java method definitions
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(public|private|protected|static|\s)+ [\w<>\[\]]+\s+(\w+)\s*\(', line)
            if match and not re.search(r'\b(class|interface|enum)\b', line):
                func_name = match.group(2)
                
                brace_count = line.count('{') - line.count('}')
                end_line = i
                
                for j in range(i, min(i + 300, len(lines))):
                    next_line = lines[j]
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0 and j > i:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+9, end_line)])
                
                functions.append({
                    'name': func_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'snippet': snippet
                })
    
    elif language == 'go':
        # Match Go function definitions
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*func\s+(\w+)\s*\(', line)
            if match:
                func_name = match.group(1)
                
                brace_count = line.count('{') - line.count('}')
                end_line = i
                
                for j in range(i, min(i + 200, len(lines))):
                    next_line = lines[j]
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+9, end_line)])
                
                functions.append({
                    'name': func_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'snippet': snippet
                })
    
    elif language in ['swift', 'kotlin']:
        # Match Swift/Kotlin function definitions
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(public|private|internal|fileprivate|open)?\s*func\s+(\w+)\s*\(', line)
            if match:
                func_name = match.group(2)
                
                brace_count = line.count('{') - line.count('}')
                end_line = i
                
                for j in range(i, min(i + 200, len(lines))):
                    next_line = lines[j]
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+9, end_line)])
                
                functions.append({
                    'name': func_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'snippet': snippet
                })
    
    elif language in ['cpp', 'csharp']:
        # Match C++/C# method definitions
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(public|private|protected|static|virtual|override|async)?\s*[\w<>\[\]]+\s+(\w+)\s*\(', line)
            if match and not re.search(r'\b(class|struct|namespace|using)\b', line):
                func_name = match.group(2)
                
                brace_count = line.count('{') - line.count('}')
                end_line = i
                
                for j in range(i, min(i + 300, len(lines))):
                    next_line = lines[j]
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0 and j > i:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+9, end_line)])
                
                functions.append({
                    'name': func_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'snippet': snippet
                })
    
    elif language == 'php':
        # Match PHP function definitions
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(public|private|protected)?\s*function\s+(\w+)\s*\(', line)
            if match:
                func_name = match.group(2)
                
                brace_count = line.count('{') - line.count('}')
                end_line = i
                
                for j in range(i, min(i + 200, len(lines))):
                    next_line = lines[j]
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+9, end_line)])
                
                functions.append({
                    'name': func_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'snippet': snippet
                })
    
    elif language == 'ruby':
        # Match Ruby method definitions
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*def\s+(\w+)', line)
            if match:
                func_name = match.group(1)
                indent = len(line) - len(line.lstrip())
                
                # Find 'end' at same indent level
                end_line = i
                for j in range(i, len(lines)):
                    next_line = lines[j]
                    if next_line.strip():
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_indent == indent and next_line.strip() == 'end':
                            end_line = j + 1
                            break
                else:
                    end_line = len(lines)
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+9, end_line)])
                
                functions.append({
                    'name': func_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'snippet': snippet
                })
    
    elif language == 'sql':
        # Match SQL stored procedures/functions
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*CREATE\s+(PROCEDURE|FUNCTION)\s+(\w+)', line, re.IGNORECASE)
            if match:
                func_name = match.group(2)
                
                # Find END statement
                end_line = i
                for j in range(i, min(i + 500, len(lines))):
                    if re.search(r'\bEND\b', lines[j], re.IGNORECASE):
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+9, end_line)])
                
                functions.append({
                    'name': func_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'snippet': snippet
                })
    
    return functions


def _extract_classes_with_lines(code: str, language: str) -> List[Dict[str, Any]]:
    """Extract classes with line numbers and method counts for multiple languages."""
    classes = []
    lines = code.split('\n')
    
    if language == 'python':
        for i, line in enumerate(lines, 1):
            match = re.match(r'^(\s*)class\s+(\w+)', line)
            if match:
                indent = len(match.group(1))
                class_name = match.group(2)
                
                # Find class end
                end_line = i
                method_count = 0
                
                for j in range(i, len(lines)):
                    next_line = lines[j]
                    if next_line.strip():
                        next_indent = len(next_line) - len(next_line.lstrip())
                        
                        # Count methods
                        if re.match(r'^\s+def\s+', next_line):
                            method_count += 1
                        
                        # Check for class end
                        if next_indent <= indent and j > i:
                            if re.match(r'^\s*(def|class)\s+', next_line):
                                end_line = j
                                break
                else:
                    end_line = len(lines)
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+14, end_line)])  # First 15 lines
                
                classes.append({
                    'name': class_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'methods': list(range(method_count)),  # Just count
                    'snippet': snippet
                })
    
    elif language in ['typescript', 'javascript']:
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(export\s+)?(class|interface)\s+(\w+)', line)
            if match:
                class_name = match.group(3)
                
                # Count methods and find class end
                brace_count = line.count('{') - line.count('}')
                end_line = i
                method_count = 0
                
                for j in range(i, min(i + 500, len(lines))):
                    next_line = lines[j]
                    
                    # Count methods
                    if re.search(r'^\s+\w+\s*\(|^\s+\w+\s*=\s*\(', next_line):
                        method_count += 1
                    
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+14, end_line)])
                
                classes.append({
                    'name': class_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'methods': list(range(method_count)),
                    'snippet': snippet
                })
    
    elif language == 'java':
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(public|private|protected)?\s*(abstract|final)?\s*class\s+(\w+)', line)
            if match:
                class_name = match.group(3)
                
                brace_count = line.count('{') - line.count('}')
                end_line = i
                method_count = 0
                
                for j in range(i, min(i + 1000, len(lines))):
                    next_line = lines[j]
                    
                    # Count methods (public/private/protected followed by type and name)
                    if re.match(r'^\s*(public|private|protected)\s+[\w<>\[\]]+\s+\w+\s*\(', next_line):
                        method_count += 1
                    
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0 and j > i:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+14, end_line)])
                
                classes.append({
                    'name': class_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'methods': list(range(method_count)),
                    'snippet': snippet
                })
    
    elif language == 'go':
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*type\s+(\w+)\s+struct', line)
            if match:
                class_name = match.group(1)
                
                brace_count = line.count('{') - line.count('}')
                end_line = i
                
                for j in range(i, min(i + 300, len(lines))):
                    next_line = lines[j]
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0:
                        end_line = j + 1
                        break
                
                # Count methods (functions with receiver)
                method_count = len(re.findall(rf'func\s+\(\w+\s+\*?{class_name}\)\s+\w+', code))
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+14, end_line)])
                
                classes.append({
                    'name': class_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'methods': list(range(method_count)),
                    'snippet': snippet
                })
    
    elif language in ['swift', 'kotlin']:
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(public|private|internal|open)?\s*(class|struct)\s+(\w+)', line)
            if match:
                class_name = match.group(3)
                
                brace_count = line.count('{') - line.count('}')
                end_line = i
                method_count = 0
                
                for j in range(i, min(i + 500, len(lines))):
                    next_line = lines[j]
                    
                    # Count methods
                    if re.search(r'^\s+func\s+\w+\s*\(', next_line):
                        method_count += 1
                    
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+14, end_line)])
                
                classes.append({
                    'name': class_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'methods': list(range(method_count)),
                    'snippet': snippet
                })
    
    elif language in ['cpp', 'csharp']:
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(public|private|protected)?\s*(class|struct)\s+(\w+)', line)
            if match:
                class_name = match.group(3)
                
                brace_count = line.count('{') - line.count('}')
                end_line = i
                method_count = 0
                
                for j in range(i, min(i + 1000, len(lines))):
                    next_line = lines[j]
                    
                    # Count methods
                    if re.match(r'^\s+(public|private|protected)?\s*[\w<>\[\]]+\s+\w+\s*\(', next_line):
                        method_count += 1
                    
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0 and j > i:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+14, end_line)])
                
                classes.append({
                    'name': class_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'methods': list(range(method_count)),
                    'snippet': snippet
                })
    
    elif language == 'php':
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*(abstract|final)?\s*class\s+(\w+)', line)
            if match:
                class_name = match.group(2)
                
                brace_count = line.count('{') - line.count('}')
                end_line = i
                method_count = 0
                
                for j in range(i, min(i + 500, len(lines))):
                    next_line = lines[j]
                    
                    # Count methods
                    if re.match(r'^\s+(public|private|protected)?\s*function\s+\w+', next_line):
                        method_count += 1
                    
                    brace_count += next_line.count('{') - next_line.count('}')
                    if brace_count == 0:
                        end_line = j + 1
                        break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+14, end_line)])
                
                classes.append({
                    'name': class_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'methods': list(range(method_count)),
                    'snippet': snippet
                })
    
    elif language == 'ruby':
        for i, line in enumerate(lines, 1):
            match = re.match(r'^\s*class\s+(\w+)', line)
            if match:
                class_name = match.group(1)
                indent = len(line) - len(line.lstrip())
                
                end_line = i
                method_count = 0
                
                for j in range(i, len(lines)):
                    next_line = lines[j]
                    if next_line.strip():
                        next_indent = len(next_line) - len(next_line.lstrip())
                        
                        # Count methods
                        if re.match(r'^\s+def\s+', next_line):
                            method_count += 1
                        
                        # Check for class end
                        if next_indent == indent and next_line.strip() == 'end':
                            end_line = j + 1
                            break
                
                line_count = end_line - i
                snippet = '\n'.join(lines[i-1:min(i+14, end_line)])
                
                classes.append({
                    'name': class_name,
                    'line_start': i,
                    'line_end': end_line,
                    'line_count': line_count,
                    'methods': list(range(method_count)),
                    'snippet': snippet
                })
    
    return classes


def _assess_docstring_coverage_simple(code: str, language: str) -> int:
    """Simple docstring coverage check for multiple languages."""
    if language == 'python':
        func_count = len(re.findall(r'^\s*def\s+\w+', code, re.MULTILINE))
        docstring_count = len(re.findall(r'^\s*""".*?"""', code, re.MULTILINE | re.DOTALL))
        if func_count == 0:
            return 100
        return int((docstring_count / func_count) * 100)
    
    elif language in ['typescript', 'javascript']:
        func_count = len(re.findall(r'function\s+\w+|const\s+\w+\s*=', code))
        comment_count = len(re.findall(r'/\*\*.*?\*/', code, re.DOTALL))
        if func_count == 0:
            return 100
        return int((comment_count / func_count) * 100)
    
    elif language in ['java', 'csharp', 'cpp']:
        func_count = len(re.findall(r'(public|private|protected)\s+[\w<>\[\]]+\s+\w+\s*\(', code))
        comment_count = len(re.findall(r'/\*\*.*?\*/', code, re.DOTALL))
        if func_count == 0:
            return 100
        return int((comment_count / func_count) * 100)
    
    elif language == 'go':
        func_count = len(re.findall(r'func\s+\w+\s*\(', code))
        comment_count = len(re.findall(r'//\s+\w+.*\n\s*func', code))
        if func_count == 0:
            return 100
        return int((comment_count / func_count) * 100)
    
    elif language in ['swift', 'kotlin']:
        func_count = len(re.findall(r'func\s+\w+\s*\(', code))
        comment_count = len(re.findall(r'/\*\*.*?\*/', code, re.DOTALL))
        if func_count == 0:
            return 100
        return int((comment_count / func_count) * 100)
    
    elif language == 'php':
        func_count = len(re.findall(r'function\s+\w+\s*\(', code))
        comment_count = len(re.findall(r'/\*\*.*?\*/', code, re.DOTALL))
        if func_count == 0:
            return 100
        return int((comment_count / func_count) * 100)
    
    elif language == 'ruby':
        func_count = len(re.findall(r'^\s*def\s+\w+', code, re.MULTILINE))
        comment_count = len(re.findall(r'^\s*#.*\n\s*def', code, re.MULTILINE))
        if func_count == 0:
            return 100
        return int((comment_count / func_count) * 100)
    
    return 50  # Default for SQL or unknown languages


# Keep the old helper functions for backwards compatibility
def _evaluate_single_responsibility(code: str, language: str) -> Dict[str, Any]:
    """Evaluate Single Responsibility Principle adherence."""
    functions = _extract_functions(code, language)
    classes = _extract_classes(code, language)
    
    # Check function length as indicator of multiple responsibilities
    long_functions = [f for f in functions if f['line_count'] > 50]
    
    # Check class method count as indicator
    classes_with_many_methods = []
    for cls in classes:
        method_count = len(cls['methods'])
        if method_count > 10:
            classes_with_many_methods.append(cls)
    
    score = 100
    if long_functions:
        score -= len(long_functions) * 10
    if classes_with_many_methods:
        score -= len(classes_with_many_methods) * 15
    
    return {
        'score': max(0, score),
        'grade': _get_grade(score),
        'issues': {
            'long_functions': len(long_functions),
            'classes_with_many_methods': len(classes_with_many_methods)
        },
        'details': {
            'long_function_names': [f['name'] for f in long_functions[:3]],
            'complex_class_names': [c['name'] for c in classes_with_many_methods[:3]]
        }
    }


def _evaluate_open_closed(code: str, language: str) -> Dict[str, Any]:
    """Evaluate Open/Closed Principle adherence."""
    # Look for extensibility patterns
    inheritance_usage = len(re.findall(r'class\s+\w+\([^)]+\)', code))
    interface_usage = len(re.findall(r'(abstract|interface)', code, re.IGNORECASE))
    composition_patterns = len(re.findall(r'self\.\w+\s*=\s*\w+\(', code))
    
    score = 50  # Base score
    score += min(inheritance_usage * 10, 30)
    score += min(interface_usage * 15, 30)
    score += min(composition_patterns * 5, 20)
    
    return {
        'score': min(100, score),
        'grade': _get_grade(score),
        'extensibility_indicators': {
            'inheritance_usage': inheritance_usage,
            'interface_usage': interface_usage,
            'composition_patterns': composition_patterns
        }
    }


def _evaluate_liskov_substitution(code: str, language: str) -> Dict[str, Any]:
    """Evaluate Liskov Substitution Principle adherence."""
    # Look for potential LSP violations
    inheritance_chains = _analyze_inheritance_chains(code, language)
    method_overrides = _detect_method_overrides(code, language)
    
    # Check for type checking in methods (potential LSP violation)
    type_checks = len(re.findall(r'isinstance\s*\(|type\s*\(.*\)\s*==', code))
    
    score = 85  # Start with good score
    if type_checks > 3:
        score -= type_checks * 5
    
    return {
        'score': max(50, score),
        'grade': _get_grade(score),
        'potential_violations': {
            'excessive_type_checking': type_checks > 3,
            'type_check_count': type_checks
        },
        'inheritance_analysis': {
            'inheritance_chains': len(inheritance_chains),
            'method_overrides': len(method_overrides)
        }
    }


def _evaluate_interface_segregation(code: str, language: str) -> Dict[str, Any]:
    """Evaluate Interface Segregation Principle adherence."""
    classes = _extract_classes(code, language)
    
    # Look for fat interfaces (classes/interfaces with many methods)
    fat_interfaces = []
    for cls in classes:
        if len(cls['methods']) > 15:
            fat_interfaces.append(cls)
    
    # Check for abstract methods/interfaces
    abstract_methods = len(re.findall(r'@abstractmethod|abstract\s+def', code, re.IGNORECASE))
    
    score = 80  # Base score
    score -= len(fat_interfaces) * 15
    score += min(abstract_methods * 5, 20)
    
    return {
        'score': max(0, score),
        'grade': _get_grade(score),
        'interface_analysis': {
            'fat_interfaces_count': len(fat_interfaces),
            'abstract_methods_count': abstract_methods,
            'fat_interface_names': [fi['name'] for fi in fat_interfaces[:3]]
        }
    }


def _evaluate_dependency_inversion(code: str, language: str) -> Dict[str, Any]:
    """Evaluate Dependency Inversion Principle adherence."""
    # Look for dependency injection patterns
    constructor_injection = len(re.findall(r'def __init__\([^)]*\w+[^)]*\):', code))
    factory_patterns = len(re.findall(r'Factory|factory|create_\w+', code))
    abstract_dependencies = len(re.findall(r'ABC|Abstract|Interface', code))
    
    # Check for direct instantiation in methods (DIP violation)
    direct_instantiations = len(re.findall(r'= \w+\(', code)) - constructor_injection
    
    score = 60  # Base score
    score += min(constructor_injection * 8, 25)
    score += min(factory_patterns * 10, 20)
    score += min(abstract_dependencies * 15, 25)
    score -= min(direct_instantiations * 3, 30)
    
    return {
        'score': max(0, min(100, score)),
        'grade': _get_grade(score),
        'dependency_patterns': {
            'constructor_injection': constructor_injection,
            'factory_patterns': factory_patterns,
            'abstract_dependencies': abstract_dependencies,
            'direct_instantiations': direct_instantiations
        }
    }


def _assess_modularity(code: str, language: str) -> Dict[str, Any]:
    """Assess code modularity."""
    imports = len(re.findall(r'^import |^from .* import', code, re.MULTILINE))
    functions = len(_extract_functions(code, language))
    classes = len(_extract_classes(code, language))
    lines_of_code = len(code.split('\n'))
    
    # Calculate modularity indicators
    functions_per_loc = functions / max(lines_of_code, 1) * 100
    classes_per_loc = classes / max(lines_of_code, 1) * 100
    imports_ratio = imports / max(lines_of_code / 100, 1)
    
    # Score based on reasonable modularity
    score = 50
    if 0.5 <= functions_per_loc <= 3:
        score += 20
    if 0.1 <= classes_per_loc <= 1:
        score += 15
    if 1 <= imports_ratio <= 10:
        score += 15
    
    return {
        'score': min(100, score),
        'grade': _get_grade(score),
        'metrics': {
            'functions_count': functions,
            'classes_count': classes,
            'imports_count': imports,
            'functions_per_100_loc': round(functions_per_loc, 2),
            'classes_per_100_loc': round(classes_per_loc, 2)
        }
    }


def _assess_separation_of_concerns(code: str, language: str) -> Dict[str, Any]:
    """Assess separation of concerns."""
    # Look for mixed concerns indicators
    mixed_concerns_indicators = {
        'ui_and_logic': len(re.findall(r'print\(.*business|logic.*print\(', code, re.IGNORECASE)),
        'data_and_presentation': len(re.findall(r'html.*data|json.*render', code, re.IGNORECASE)),
        'multiple_responsibilities': len(re.findall(r'def \w*(save|load|process|validate|render)\w*', code))
    }
    
    total_mixed_concerns = sum(mixed_concerns_indicators.values())
    score = max(0, 100 - total_mixed_concerns * 10)
    
    return {
        'score': score,
        'grade': _get_grade(score),
        'mixed_concerns_indicators': mixed_concerns_indicators,
        'separation_quality': 'good' if score >= 80 else 'needs_improvement' if score >= 60 else 'poor'
    }


def _evaluate_naming_conventions(code: str, language: str) -> Dict[str, Any]:
    """Evaluate naming conventions."""
    functions = _extract_functions(code, language)
    classes = _extract_classes(code, language)
    variables = _extract_variables(code, language)
    
    naming_issues = {
        'snake_case_functions': 0,
        'pascal_case_classes': 0,
        'descriptive_names': 0,
        'abbreviations': 0
    }
    
    # Check function naming (should be snake_case in Python)
    if language.lower() == 'python':
        for func in functions:
            if not re.match(r'^[a-z_][a-z0-9_]*$', func['name']):
                naming_issues['snake_case_functions'] += 1
    
    # Check class naming (should be PascalCase)
    for cls in classes:
        if not re.match(r'^[A-Z][a-zA-Z0-9]*$', cls['name']):
            naming_issues['pascal_case_classes'] += 1
    
    # Check for descriptive names (length > 3)
    short_names = [name for name in variables if len(name) <= 2 and name not in ['i', 'j', 'k', 'x', 'y', 'z']]
    naming_issues['descriptive_names'] = len(short_names)
    
    # Check for excessive abbreviations
    abbreviations = len([name for name in variables if len(name) <= 5 and name.count('_') == 0 and name.islower()])
    naming_issues['abbreviations'] = abbreviations
    
    total_issues = sum(naming_issues.values())
    score = max(0, 100 - total_issues * 5)
    
    return {
        'score': score,
        'grade': _get_grade(score),
        'naming_issues': naming_issues,
        'conventions_followed': score >= 80
    }


def _evaluate_code_structure(code: str, language: str) -> Dict[str, Any]:
    """Evaluate overall code structure."""
    lines = code.split('\n')
    
    structure_metrics = {
        'empty_lines_ratio': len([line for line in lines if not line.strip()]) / max(len(lines), 1),
        'comment_lines': len([line for line in lines if line.strip().startswith('#')]),
        'average_line_length': sum(len(line) for line in lines) / max(len(lines), 1),
        'max_line_length': max(len(line) for line in lines) if lines else 0,
        'indentation_consistency': _check_indentation_consistency(lines)
    }
    
    score = 100
    # Penalize for poor structure
    if structure_metrics['empty_lines_ratio'] < 0.05 or structure_metrics['empty_lines_ratio'] > 0.3:
        score -= 10
    if structure_metrics['average_line_length'] > 100:
        score -= 15
    if structure_metrics['max_line_length'] > 120:
        score -= 10
    if not structure_metrics['indentation_consistency']:
        score -= 20
    
    return {
        'score': max(0, score),
        'grade': _get_grade(score),
        'structure_metrics': structure_metrics
    }


def _assess_docstring_coverage(code: str, language: str) -> Dict[str, Any]:
    """Assess docstring coverage."""
    functions = _extract_functions(code, language)
    classes = _extract_classes(code, language)
    
    functions_with_docstrings = 0
    classes_with_docstrings = 0
    
    # Count functions with docstrings
    for func in functions:
        if '"""' in func.get('body', '') or "'''" in func.get('body', ''):
            functions_with_docstrings += 1
    
    # Count classes with docstrings
    for cls in classes:
        if '"""' in cls.get('body', '') or "'''" in cls.get('body', ''):
            classes_with_docstrings += 1
    
    total_items = len(functions) + len(classes)
    documented_items = functions_with_docstrings + classes_with_docstrings
    
    coverage_percentage = (documented_items / max(total_items, 1)) * 100
    
    return {
        'coverage_percentage': round(coverage_percentage, 2),
        'grade': _get_grade(coverage_percentage),
        'documented_functions': functions_with_docstrings,
        'total_functions': len(functions),
        'documented_classes': classes_with_docstrings,
        'total_classes': len(classes)
    }


def _assess_comment_quality(code: str, language: str) -> Dict[str, Any]:
    """Assess comment quality."""
    lines = code.split('\n')
    comment_lines = [line for line in lines if line.strip().startswith('#')]
    
    # Analyze comment quality
    quality_indicators = {
        'explanatory_comments': len([c for c in comment_lines if len(c.strip()) > 20]),
        'todo_comments': len([c for c in comment_lines if 'TODO' in c.upper()]),
        'inline_comments': len([line for line in lines if '#' in line and not line.strip().startswith('#')]),
        'commented_code': len([c for c in comment_lines if any(keyword in c for keyword in ['def ', 'class ', 'import ', 'return '])])
    }
    
    total_comments = len(comment_lines)
    good_comments = quality_indicators['explanatory_comments']
    
    if total_comments == 0:
        quality_score = 0
    else:
        quality_score = (good_comments / total_comments) * 100
    
    return {
        'quality_score': round(quality_score, 2),
        'grade': _get_grade(quality_score),
        'quality_indicators': quality_indicators,
        'total_comments': total_comments
    }


def _check_readme_indicators(code: str) -> Dict[str, Any]:
    """Check for README and documentation indicators."""
    readme_indicators = {
        'has_main_guard': '__name__ == "__main__"' in code,
        'has_module_docstring': code.strip().startswith('"""') or code.strip().startswith("'''"),
        'has_usage_examples': 'example' in code.lower() or 'usage' in code.lower(),
        'has_version_info': '__version__' in code or 'version' in code.lower()
    }
    
    score = sum(readme_indicators.values()) * 25
    
    return {
        'score': score,
        'grade': _get_grade(score),
        'indicators': readme_indicators
    }


def _check_api_documentation(code: str, language: str) -> Dict[str, Any]:
    """Check for API documentation patterns."""
    api_patterns = {
        'type_hints': len(re.findall(r':\s*\w+', code)),
        'return_annotations': len(re.findall(r'->\s*\w+:', code)),
        'docstring_parameters': len(re.findall(r'Args:|Parameters:|Param:', code)),
        'docstring_returns': len(re.findall(r'Returns:|Return:', code))
    }
    
    total_patterns = sum(api_patterns.values())
    score = min(100, total_patterns * 5)
    
    return {
        'score': score,
        'grade': _get_grade(score),
        'api_patterns': api_patterns
    }


def _assess_testing_practices(code: str, language: str) -> Dict[str, Any]:
    """Assess testing practices."""
    test_indicators = {
        'test_functions': len(re.findall(r'def test_\w+', code)),
        'assert_statements': len(re.findall(r'assert\s+', code)),
        'test_imports': len(re.findall(r'import (unittest|pytest|nose)', code)),
        'mock_usage': len(re.findall(r'mock|Mock|patch', code)),
        'fixture_usage': len(re.findall(r'@pytest\.fixture|setUp|tearDown', code))
    }
    
    total_test_indicators = sum(test_indicators.values())
    score = min(100, total_test_indicators * 10)
    
    return {
        'score': score,
        'grade': _get_grade(score),
        'test_indicators': test_indicators,
        'has_tests': total_test_indicators > 0
    }


def _assess_test_coverage_hints(code: str, language: str) -> Dict[str, Any]:
    """Assess test coverage hints."""
    functions = _extract_functions(code, language)
    test_functions = [f for f in functions if f['name'].startswith('test_')]
    regular_functions = [f for f in functions if not f['name'].startswith('test_')]
    
    if len(regular_functions) == 0:
        coverage_hint = 100
    else:
        coverage_hint = (len(test_functions) / len(regular_functions)) * 100
    
    return {
        'coverage_hint_percentage': min(100, round(coverage_hint, 2)),
        'grade': _get_grade(coverage_hint),
        'test_functions': len(test_functions),
        'regular_functions': len(regular_functions)
    }


def _assess_test_quality(code: str, language: str) -> Dict[str, Any]:
    """Assess test quality."""
    test_quality_indicators = {
        'descriptive_test_names': len([m.group() for m in re.finditer(r'def test_\w{10,}', code)]),
        'test_docstrings': len([m.group() for m in re.finditer(r'def test_.*?""".*?"""', code, re.DOTALL)]),
        'setup_teardown': len(re.findall(r'setUp|tearDown|setup_method|teardown_method', code)),
        'parameterized_tests': len(re.findall(r'@pytest\.mark\.parametrize|@parameterized', code))
    }
    
    total_quality = sum(test_quality_indicators.values())
    score = min(100, total_quality * 15)
    
    return {
        'score': score,
        'grade': _get_grade(score),
        'quality_indicators': test_quality_indicators
    }


def _identify_testing_patterns(code: str, language: str) -> List[str]:
    """Identify testing patterns used."""
    patterns = []
    
    if 'unittest' in code:
        patterns.append('unittest')
    if 'pytest' in code:
        patterns.append('pytest')
    if 'mock' in code.lower():
        patterns.append('mocking')
    if '@pytest.fixture' in code:
        patterns.append('fixtures')
    if 'setUp' in code or 'tearDown' in code:
        patterns.append('setup_teardown')
    
    return patterns


def _evaluate_exception_handling(code: str, language: str) -> Dict[str, Any]:
    """Evaluate exception handling practices."""
    exception_patterns = {
        'try_blocks': len(re.findall(r'try:', code)),
        'except_blocks': len(re.findall(r'except\s+\w+:', code)),
        'generic_except': len(re.findall(r'except:', code)),
        'finally_blocks': len(re.findall(r'finally:', code)),
        'raise_statements': len(re.findall(r'raise\s+\w+', code))
    }
    
    # Score based on good exception handling practices
    score = 50
    if exception_patterns['try_blocks'] > 0:
        score += 20
    if exception_patterns['except_blocks'] > exception_patterns['generic_except']:
        score += 20
    if exception_patterns['finally_blocks'] > 0:
        score += 10
    
    # Penalize for bad practices
    if exception_patterns['generic_except'] > 0:
        score -= exception_patterns['generic_except'] * 10
    
    return {
        'score': max(0, min(100, score)),
        'grade': _get_grade(score),
        'exception_patterns': exception_patterns
    }


def _evaluate_error_recovery(code: str, language: str) -> Dict[str, Any]:
    """Evaluate error recovery mechanisms."""
    recovery_patterns = {
        'retry_logic': len(re.findall(r'retry|attempt', code, re.IGNORECASE)),
        'fallback_mechanisms': len(re.findall(r'fallback|default|backup', code, re.IGNORECASE)),
        'circuit_breaker': len(re.findall(r'circuit.*breaker', code, re.IGNORECASE)),
        'timeout_handling': len(re.findall(r'timeout|deadline', code, re.IGNORECASE))
    }
    
    total_recovery = sum(recovery_patterns.values())
    score = min(100, total_recovery * 20)
    
    return {
        'score': score,
        'grade': _get_grade(score),
        'recovery_patterns': recovery_patterns
    }


def _evaluate_logging_practices(code: str, language: str) -> Dict[str, Any]:
    """Evaluate logging practices."""
    logging_patterns = {
        'logging_imports': len(re.findall(r'import logging|from logging', code)),
        'log_statements': len(re.findall(r'log\.\w+\(|logging\.\w+\(', code)),
        'log_levels': len(re.findall(r'(debug|info|warning|error|critical)', code, re.IGNORECASE)),
        'structured_logging': len(re.findall(r'extra=|exc_info=', code))
    }
    
    total_logging = sum(logging_patterns.values())
    score = min(100, total_logging * 15)
    
    return {
        'score': score,
        'grade': _get_grade(score),
        'logging_patterns': logging_patterns
    }


def _assess_algorithm_efficiency(code: str, language: str) -> Dict[str, Any]:
    """Assess algorithm efficiency indicators."""
    efficiency_patterns = {
        'nested_loops': len(re.findall(r'for.*for', code, re.DOTALL)),
        'recursive_calls': len(re.findall(r'def \w+.*\1\(', code)),
        'list_comprehensions': len(re.findall(r'\[.*for.*in.*\]', code)),
        'generator_expressions': len(re.findall(r'\(.*for.*in.*\)', code)),
        'builtin_functions': len(re.findall(r'(map|filter|reduce|sorted|min|max)\(', code))
    }
    
    # Score based on efficiency indicators
    score = 70  # Base score
    score -= efficiency_patterns['nested_loops'] * 10  # Nested loops reduce efficiency
    score += efficiency_patterns['list_comprehensions'] * 5
    score += efficiency_patterns['generator_expressions'] * 5
    score += efficiency_patterns['builtin_functions'] * 3
    
    return {
        'score': max(0, min(100, score)),
        'grade': _get_grade(score),
        'efficiency_patterns': efficiency_patterns
    }


def _assess_resource_management(code: str, language: str) -> Dict[str, Any]:
    """Assess resource management practices."""
    resource_patterns = {
        'context_managers': len(re.findall(r'with\s+\w+', code)),
        'file_operations': len(re.findall(r'open\(', code)),
        'connection_handling': len(re.findall(r'connect\(|connection', code, re.IGNORECASE)),
        'memory_optimization': len(re.findall(r'del\s+\w+|gc\.collect', code))
    }
    
    # Score based on proper resource management
    score = 50
    if resource_patterns['context_managers'] > 0 and resource_patterns['file_operations'] > 0:
        score += 25  # Using context managers with file operations
    if resource_patterns['connection_handling'] > 0:
        score += 15
    score += resource_patterns['memory_optimization'] * 10
    
    return {
        'score': min(100, score),
        'grade': _get_grade(score),
        'resource_patterns': resource_patterns
    }


def _identify_caching_strategies(code: str, language: str) -> Dict[str, Any]:
    """Identify caching strategies."""
    caching_patterns = {
        'lru_cache': len(re.findall(r'@lru_cache|@cache', code)),
        'memoization': len(re.findall(r'memo|cache', code, re.IGNORECASE)),
        'redis_cache': len(re.findall(r'redis|Redis', code)),
        'in_memory_cache': len(re.findall(r'cache.*dict|dict.*cache', code, re.IGNORECASE))
    }
    
    total_caching = sum(caching_patterns.values())
    score = min(100, total_caching * 25)
    
    return {
        'score': score,
        'grade': _get_grade(score),
        'caching_patterns': caching_patterns,
        'has_caching': total_caching > 0
    }


# Helper functions

def _extract_functions(code: str, language: str) -> List[Dict[str, Any]]:
    """Extract function information from code."""
    functions = []
    if language.lower() == 'python':
        pattern = r'def\s+(\w+)\s*\([^)]*\):'
        matches = re.finditer(pattern, code)
        for match in matches:
            func_start = match.start()
            func_name = match.group(1)
            # Rough estimate of function body
            remaining_code = code[func_start:]
            lines = remaining_code.split('\n')
            func_lines = []
            indent_level = len(lines[0]) - len(lines[0].lstrip())
            
            for i, line in enumerate(lines[1:], 1):
                if line.strip() and len(line) - len(line.lstrip()) <= indent_level and line[0] not in [' ', '\t']:
                    break
                func_lines.append(line)
            
            functions.append({
                'name': func_name,
                'line_count': len(func_lines),
                'body': '\n'.join(func_lines)
            })
    
    return functions


def _extract_classes(code: str, language: str) -> List[Dict[str, Any]]:
    """Extract class information from code."""
    classes = []
    if language.lower() == 'python':
        pattern = r'class\s+(\w+)(?:\([^)]*\))?:'
        matches = re.finditer(pattern, code)
        for match in matches:
            class_name = match.group(1)
            class_start = match.start()
            # Find methods in class
            remaining_code = code[class_start:]
            methods = re.findall(r'def\s+(\w+)\s*\([^)]*\):', remaining_code)
            
            classes.append({
                'name': class_name,
                'methods': methods,
                'body': remaining_code[:500]  # First 500 chars for analysis
            })
    
    return classes


def _extract_variables(code: str, language: str) -> List[str]:
    """Extract variable names from code."""
    # Simple variable extraction
    variables = []
    if language.lower() == 'python':
        # Find assignment patterns
        assignments = re.findall(r'(\w+)\s*=\s*', code)
        variables.extend(assignments)
        
        # Find function parameters
        func_params = re.findall(r'def\s+\w+\s*\(([^)]*)\)', code)
        for params in func_params:
            param_names = re.findall(r'(\w+)(?:\s*=|,|$)', params)
            variables.extend(param_names)
    
    return list(set(variables))  # Remove duplicates


def _analyze_inheritance_chains(code: str, language: str) -> List[Dict[str, Any]]:
    """Analyze inheritance chains."""
    chains = []
    if language.lower() == 'python':
        pattern = r'class\s+(\w+)\s*\(([^)]+)\):'
        matches = re.finditer(pattern, code)
        for match in matches:
            child_class = match.group(1)
            parent_classes = [p.strip() for p in match.group(2).split(',')]
            chains.append({
                'child': child_class,
                'parents': parent_classes
            })
    
    return chains


def _detect_method_overrides(code: str, language: str) -> List[str]:
    """Detect method overrides."""
    overrides = []
    if language.lower() == 'python':
        # Look for common override patterns
        override_patterns = [
            r'def __init__\(',
            r'def __str__\(',
            r'def __repr__\(',
            r'def __eq__\(',
            r'def __hash__\('
        ]
        
        for pattern in override_patterns:
            matches = re.findall(pattern, code)
            overrides.extend(matches)
    
    return overrides


def _check_indentation_consistency(lines: List[str]) -> bool:
    """Check if indentation is consistent."""
    indents = []
    for line in lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if indent > 0:
                indents.append(indent)
    
    if not indents:
        return True
    
    # Check if all indentations are multiples of the smallest indent
    min_indent = min(indents)
    if min_indent == 0:
        return True
    
    return all(indent % min_indent == 0 for indent in indents)


def _calculate_overall_scores(practices_result: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overall scores from all evaluations."""
    solid_scores = []
    for principle, data in practices_result['solid_principles'].items():
        if isinstance(data, dict) and 'score' in data:
            solid_scores.append(data['score'])
    
    overall_solid_score = sum(solid_scores) / len(solid_scores) if solid_scores else 0
    
    org_scores = []
    for aspect, data in practices_result['code_organization'].items():
        if isinstance(data, dict) and 'score' in data:
            org_scores.append(data['score'])
    
    overall_organization_score = sum(org_scores) / len(org_scores) if org_scores else 0
    
    # Calculate weighted overall score
    overall_score = (
        overall_solid_score * 0.3 +
        overall_organization_score * 0.25 +
        practices_result['documentation_quality']['docstring_coverage']['coverage_percentage'] * 0.2 +
        practices_result['testing_practices']['score'] * 0.25
    )
    
    return {
        'overall_engineering_score': round(overall_score, 2),
        'solid_principles_score': round(overall_solid_score, 2),
        'code_organization_score': round(overall_organization_score, 2),
        'overall_grade': _get_grade(overall_score)
    }


def _generate_engineering_recommendations(practices_result: Dict[str, Any]) -> List[str]:
    """Generate engineering practice recommendations."""
    recommendations = []
    
    # SOLID principles recommendations
    solid_scores = practices_result['solid_principles']
    if solid_scores['single_responsibility']['score'] < 70:
        recommendations.append("Break down large functions and classes to follow Single Responsibility Principle")
    
    if solid_scores['dependency_inversion']['score'] < 70:
        recommendations.append("Implement dependency injection to improve testability and flexibility")
    
    # Documentation recommendations
    doc_coverage = practices_result['documentation_quality']['docstring_coverage']['coverage_percentage']
    if doc_coverage < 50:
        recommendations.append("Add docstrings to functions and classes to improve code documentation")
    
    # Testing recommendations
    if practices_result['testing_practices']['score'] < 60:
        recommendations.append("Implement comprehensive unit tests to improve code reliability")
    
    # Code organization recommendations
    if practices_result['code_organization']['naming_conventions']['score'] < 70:
        recommendations.append("Follow consistent naming conventions (snake_case for functions, PascalCase for classes)")
    
    # Error handling recommendations
    if practices_result['error_handling']['exception_handling']['score'] < 60:
        recommendations.append("Implement proper exception handling with specific exception types")
    
    if not recommendations:
        recommendations.append("Engineering practices are well-implemented - maintain current quality standards")
    
    return recommendations


def _get_grade(score: float) -> str:
    """Convert numeric score to letter grade."""
    if score >= 90:
        return 'A'
    elif score >= 80:
        return 'B'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'F'