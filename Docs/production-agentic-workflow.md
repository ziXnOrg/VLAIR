---
description: Production-Ready Agentic Software Engineering Workflow - Optimized for Quality → Clarity → Reliability → Speed
globs: []
alwaysApply: true
---

# Production Agentic Workflow: Quality-First Engineering

## Optimization Priority

**Quality** → **Clarity** → **Reliability** → **Speed**

This workflow prioritizes:
1. **Quality**: Excellent code that solves problems correctly and elegantly
2. **Clarity**: Code that is understandable, maintainable, and well-documented
3. **Reliability**: Code that works consistently and handles edge cases
4. **Speed**: Efficient execution (but never at the expense of the above)

## Core Principles

### 1. Quality Through Thought Frameworks

Every task begins with selecting the appropriate reasoning strategy:

**For Standard Tasks**: Chain-of-Thought (CoT)
```
Break problem → Solve step-by-step → Validate each step
```

**For Complex Problems**: Strategic CoT or Tree of Thoughts
```
Identify optimal strategy → Apply systematically → Verify alignment
```

**For Novel Challenges**: First Principles
```
Strip to fundamentals → Rebuild from scratch → Validate against core needs
```

**For Exploration**: ReAct Loop
```
Reason → Act → Observe → Iterate until complete
```

### 2. Clarity Through Communication

**Before Every Action**:
```
THOUGHT PROCESS:
─────────────────
Goal: [What we're trying to achieve]

Current Understanding:
  • What we know: [facts]
  • What we don't know: [gaps]
  • Assumptions: [list any]

Approach:
  1. [Step 1 - why this matters]
  2. [Step 2 - how it connects]
  3. [Step 3 - expected outcome]

Risks & Mitigations:
  • Risk: [potential issue] → Mitigation: [how to handle]

Success Criteria:
  • [How we know it works]

Confidence: [0.0-1.0]

Proceed? [Y/N]
```

**After Every Significant Action**:
```
REFLECTION:
───────────
What was done: [description]

Quality assessment:
  ✓ Works correctly: [Y/N]
  ✓ Code is clear: [Y/N]
  ✓ Edge cases handled: [Y/N]
  ✓ Well documented: [Y/N]

What could be better: [improvements]

Ready to continue? [Y/N]
```

### 3. Reliability Through Iterative Refinement

**Pattern**:
```
Iteration Loop (max: 5 iterations per component):
  
  1. GENERATE
     ├─ Apply thought framework
     ├─ Create implementation
     └─ Add documentation inline
     
  2. CRITIQUE
     ├─ Does it solve the problem correctly?
     ├─ Is the code clear and readable?
     ├─ Are edge cases handled?
     ├─ Is error handling comprehensive?
     ├─ Does it follow project patterns?
     └─ Is it maintainable?
     
  3. REFINE
     ├─ Select ONE issue to improve
     ├─ Make targeted change
     └─ Validate change works
     
  4. VERIFY
     ├─ Run relevant tests
     ├─ Check linting
     ├─ Validate types
     └─ Decision: KEEP or REVERT
     
  5. ITERATE OR COMPLETE
     ├─ Quality threshold met? → COMPLETE
     ├─ Improvements possible? → CONTINUE
     └─ Max iterations reached? → REVIEW WITH HUMAN
```

### 4. Speed Through Smart Context Management

**Stratified Context Retrieval** (inspired by AutoCodeRover):

```
LAYER 1 - High-Level Scan:
  Input: Task description
  Load: Module structure, key classes
  Decide: Relevant areas identified? [Y/N]

LAYER 2 - Targeted Dive:
  Input: Layer 1 results + task
  Load: Specific class/function implementations
  Decide: Sufficient understanding? [Y/N]

LAYER 3 - Precision Focus:
  Input: All previous context
  Load: Exact modification points + dependencies
  Decide: Ready to implement? [Y/N]

Exit when: Sufficient context OR max layers (5)
```

## Complete Workflow Execution

### Phase 1: Understanding

```
📖 UNDERSTANDING PHASE
══════════════════════

1. Parse Request
   • Read user's request carefully
   • Identify explicit requirements
   • Note implicit expectations
   • List any ambiguities

2. Clarify Ambiguities
   ❓ Questions for human:
   • [Question 1]
   • [Question 2]
   
   Wait for answers before proceeding

3. Restate Understanding
   "My understanding is:
    - Goal: [restate in own words]
    - Success looks like: [concrete definition]
    - Out of scope: [what we won't do]
    
    Is this correct? [Y/N]"

4. Select Thought Framework
   Based on task type:
   • Standard → CoT
   • Complex → SCoT or ToT
   • Novel → First Principles
   • Exploratory → ReAct
   
   Justification: [why this framework]

✓ Phase Complete when understanding confirmed
```

### Phase 2: Planning

```
📋 PLANNING PHASE
═════════════════

1. Decompose Task
   High-level breakdown:
   □ Task 1: [description]
     ├─ Complexity: [Low/Med/High]
     ├─ Dependencies: [none or list]
     └─ Verification: [how to test]
   
   □ Task 2: [description]
     └─ [same structure]
   
   [Continue for all tasks]

2. Identify Context Needs
   Files to understand:
   • [file 1] - Why: [reason]
   • [file 2] - Why: [reason]
   
   Knowledge gaps:
   • [gap 1] - How to fill: [approach]

3. Define Success Criteria
   This task is complete when:
   □ [Criterion 1] - measurable
   □ [Criterion 2] - measurable
   □ [Criterion 3] - measurable
   
   Quality gates:
   □ Tests pass
   □ Code reviewed
   □ Documentation updated
   □ No linting errors

4. Estimate Confidence
   Confidence in plan: [0.0-1.0]
   
   If < 0.7:
     Concerns: [list]
     Need: [what would increase confidence]

5. Human Approval Gate
   ⏸️ PLAN REVIEW REQUIRED
   
   Show complete plan to human
   Get approval before implementation
   
   Adjustments requested: [if any]

✓ Phase Complete when plan approved
```

### Phase 3: Context Gathering

```
🔍 CONTEXT GATHERING PHASE
═══════════════════════════

Using Stratified Search:

┌─ STRATUM 1 ─────────────────┐
│ Scope: High-level structure  │
│ Goal: Identify relevant areas│
│                              │
│ Search for:                  │
│ • Classes matching [keywords]│
│ • Methods matching [keywords]│
│ • Files containing [concepts]│
│                              │
│ Results: [summary]           │
│ Sufficient? [Y/N]            │
└──────────────────────────────┘

If N, continue:

┌─ STRATUM 2 ─────────────────┐
│ Scope: Implementation details│
│ Input: Stratum 1 + task      │
│                              │
│ Retrieve:                    │
│ • Full method implementations│
│ • Class structures           │
│ • Dependencies               │
│                              │
│ Results: [summary]           │
│ Sufficient? [Y/N]            │
└──────────────────────────────┘

Continue until sufficient or max strata

Final Context Summary:
  Files loaded: [count]
  Key components: [list]
  Dependencies: [list]
  Ready to implement: [Y/N]

✓ Phase Complete when context sufficient
```

### Phase 4: Implementation (Test-Driven)

```
🔨 IMPLEMENTATION PHASE
═══════════════════════

For each task:

┌─ RED: Write Test ────────────┐
│                              │
│ 1. Convert acceptance        │
│    criteria to test case     │
│                              │
│ 2. Implement test:           │
│    • Arrange (setup)         │
│    • Act (execute)           │
│    • Assert (verify)         │
│                              │
│ 3. Run test (expect FAIL)    │
│                              │
│ 4. Verify failure reason     │
│    correct                   │
│                              │
│ ✓ Test fails for right reason│
└──────────────────────────────┘

┌─ GREEN: Make Test Pass ──────┐
│                              │
│ 1. Apply thought framework   │
│    to design solution        │
│                              │
│ 2. Implement MINIMAL code    │
│    to pass test              │
│                              │
│ 3. Add inline documentation  │
│    explaining approach       │
│                              │
│ 4. Run test (expect PASS)    │
│                              │
│ ✓ Test passes                │
└──────────────────────────────┘

┌─ REFACTOR: Improve Quality ──┐
│                              │
│ Iterative Refinement:        │
│                              │
│ Iteration 1:                 │
│   • Critique: [issue found]  │
│   • Refine: [improvement]    │
│   • Verify: Tests still pass │
│                              │
│ Iteration 2:                 │
│   • Critique: [issue found]  │
│   • Refine: [improvement]    │
│   • Verify: Tests still pass │
│                              │
│ [Continue until excellent]   │
│                              │
│ Final check:                 │
│ ✓ Code is clear              │
│ ✓ Well documented            │
│ ✓ Handles edge cases         │
│ ✓ Error handling complete    │
│ ✓ Follows patterns           │
└──────────────────────────────┘

Repeat for each task

✓ Phase Complete when all tasks implemented
```

### Phase 5: Verification

```
✅ VERIFICATION PHASE
══════════════════════

Comprehensive Validation:

1. Test Suite
   □ Run full test suite
   □ All tests pass?
   
   If N:
     • Analyze failures
     • Fix issues
     • Retest
     • Repeat until all pass

2. Code Quality
   □ Linting: [result]
   □ Type checking: [result]
   □ Complexity metrics: [acceptable?]
   □ Code coverage: [percentage]
   
   If issues:
     • List problems
     • Fix each
     • Re-verify

3. Documentation
   □ All functions documented?
   □ Complex logic explained?
   □ Examples provided?
   □ README updated?

4. Edge Cases
   Review implementation:
   • What could go wrong? [list]
   • How is each handled? [verify]
   • Additional tests needed? [add]

5. Integration Check
   □ Integrates with existing code?
   □ No breaking changes?
   □ Dependencies satisfied?
   □ API contracts maintained?

6. Human Review Gate
   ⏸️ VERIFICATION REVIEW
   
   Show results to human:
   • What was implemented
   • Test results
   • Quality metrics
   • Files changed
   
   Approval: [Y/N]

✓ Phase Complete when all checks pass
```

### Phase 6: Reflection & Documentation

```
📝 REFLECTION PHASE
════════════════════

1. Implementation Summary
   ┌────────────────────────────┐
   │ WHAT WAS BUILT             │
   ├────────────────────────────┤
   │ Feature: [name]            │
   │ Files modified: [count]    │
   │ Tests added: [count]       │
   │ Lines changed: [estimate]  │
   └────────────────────────────┘

2. Approach Reflection
   Strategy used: [framework]
   
   What went well:
   • [Success 1]
   • [Success 2]
   
   What was challenging:
   • [Challenge 1] - How solved: [approach]
   • [Challenge 2] - How solved: [approach]
   
   Learnings:
   • [Lesson 1]
   • [Lesson 2]

3. Quality Self-Assessment
   Quality (1-10): [score]
   Clarity (1-10): [score]
   Reliability (1-10): [score]
   
   Justification: [reasoning]

4. Improvement Opportunities
   Optional enhancements identified:
   
   1. [Enhancement 1]
      Impact: [High/Med/Low]
      Effort: [estimate]
      Justification: [why valuable]
   
   2. [Enhancement 2]
      [same structure]
   
   Pursue these? [Y/N/Select]

5. Documentation Update
   □ Inline comments clear?
   □ Function docstrings complete?
   □ README reflects changes?
   □ Architecture docs updated?
   □ Examples added/updated?

✓ Phase Complete when documented
```

## Human-in-the-Loop Integration

### Mandatory Approval Gates

```
Gate 1: AFTER PLANNING
├─ Show: Complete task breakdown
├─ Show: Approach and thought framework
├─ Show: Success criteria
└─ Wait: Human approval

Gate 2: BEFORE MAJOR CHANGES
├─ Show: Files to be modified
├─ Show: Scope of changes
├─ Show: Potential risks
└─ Wait: Human approval

Gate 3: AFTER TEST FAILURES  
├─ Show: Failed tests
├─ Show: Root cause analysis
├─ Show: Proposed fix
└─ Wait: Human decision

Gate 4: BEFORE COMMIT
├─ Show: All changes summary
├─ Show: Test results
├─ Show: Quality metrics
└─ Wait: Final approval
```

### Progress Updates

Every 3-5 operations:
```
📊 PROGRESS UPDATE [N/M complete]

Current: [what I'm doing now]
Last completed: [previous task]
Next: [upcoming task]

Status:
  ✓ Going well: [aspect]
  ⚠️ Concern: [if any]

Confidence: [0.0-1.0]
```

## Error Handling & Recovery

```
When error encountered:

1. STOP immediately
2. Classify error:
   • Syntax → Parse error
   • Logic → Wrong implementation
   • Test → Failure in verification
   • Environment → Missing dependency
   • Unknown → Need investigation

3. Analyze:
   Error: [description]
   Context: [what was being done]
   Cause: [root cause analysis]

4. Propose recovery:
   Option A: [approach 1]
   Option B: [approach 2]
   Recommended: [which and why]

5. Human decision:
   ⏸️ ERROR RECOVERY DECISION NEEDED
   
   Present analysis and options
   Wait for human choice

6. Execute recovery:
   Follow human guidance
   Verify recovery successful
   Document what was learned
```

## Quality Standards

### Code Must Have

```
✓ Clear Function Names
  - Verb-based for actions
  - Descriptive of purpose
  - Follows project conventions

✓ Comprehensive Docstrings
  """
  Brief description of purpose.
  
  Args:
      param1 (type): Description
      param2 (type): Description
  
  Returns:
      type: Description
  
  Raises:
      ErrorType: When this occurs
  
  Example:
      >>> example_usage()
      expected_output
  """

✓ Inline Comments
  - Explain WHY, not WHAT
  - Complex logic explained
  - Edge case handling noted

✓ Error Handling
  - Input validation
  - Try-except blocks
  - Meaningful error messages
  - Graceful degradation

✓ Type Annotations
  def function(param: str) -> Dict[str, Any]:
      ...

✓ Tests
  - Unit tests for all functions
  - Edge cases covered
  - Error cases tested
  - Integration tests for endpoints
```

### Code Must Not Have

```
✗ Magic numbers
  Use: MAX_RETRIES = 3
  Not: for i in range(3):

✗ Unclear variable names
  Use: user_authentication_token
  Not: uat or x

✗ Missing error handling
  Use: try-except with specific errors
  Not: bare except or none at all

✗ Undocumented assumptions
  Document: "Assumes input is sorted"

✗ Copy-paste duplication
  Extract: Shared logic to function

✗ TODO without tracking
  Use: TODO(#123): Description
  Not: TODO: fix this later
```

## Workflow Optimization for Quality

### Favor Quality Over Speed

**When tempted to rush**:
```
STOP and ask:
  • Is this code clear enough?
  • Are edge cases handled?
  • Is it well tested?
  • Will my future self understand this?
  
If N to any: REFINE before continuing
```

**Quality Checklist** (before moving on):
```
□ Code does what it should
□ Code is easy to understand
□ Edge cases are handled  
□ Error handling is complete
□ Tests are comprehensive
□ Documentation is clear
□ Patterns are followed
□ No technical debt added
```

### Maximize Clarity

**Clarity Principles**:
```
1. Explicit > Implicit
   Prefer: clear_variable_name
   Over: short_name
   
2. Simple > Clever
   Prefer: readable_code
   Over: one_liner_magic
   
3. Documented > Self-Explanatory
   Even "obvious" code benefits from:
   - Purpose explanation
   - Context provision
   - Edge case notes
```

### Ensure Reliability

**Reliability Checklist**:
```
□ Works with normal inputs
□ Works with edge cases:
  • Empty inputs
  • Null/None values
  • Maximum values
  • Minimum values
  • Invalid types
□ Handles errors gracefully
□ Degrades gracefully under load
□ Thread-safe (if concurrent)
□ Resource cleanup handled
```

## Complete Example Execution

```
═══════════════════════════════════════════
TASK: Add Redis caching to user profile API
═══════════════════════════════════════════

─── UNDERSTANDING ───
Goal: Reduce database load by caching user profiles
Success: Response time < 100ms for cached requests
Framework: Strategic CoT (optimization problem)
✓ Understanding confirmed

─── PLANNING ───
Tasks:
  1. Design cache key strategy
  2. Implement cache wrapper
  3. Add cache invalidation
  4. Write tests
  5. Update documentation

Context needs: user_profile.py, cache.py
✓ Plan approved

─── CONTEXT GATHERING ───
Stratum 1: Located UserProfile class
Stratum 2: Retrieved get_profile() implementation
Stratum 3: Found existing cache utilities
✓ Context sufficient

─── IMPLEMENTATION ───

Task 1: Design cache key strategy
  RED: Test cache key generation
  GREEN: Implement hash-based keys
  REFACTOR: Add documentation
  ✓ Complete

Task 2: Implement cache wrapper
  RED: Test caching behavior
  GREEN: Add cache decorator
  REFACTOR: 
    - Iteration 1: Improve error handling
    - Iteration 2: Add logging
  ✓ Complete

[Continue for remaining tasks]

─── VERIFICATION ───
✓ All tests pass (25/25)
✓ Linting clean
✓ Type checking passed
✓ Coverage: 92%
✓ Documentation updated
✓ Human approved

─── REFLECTION ───
Implementation successful
Quality: 9/10 - Well tested and documented
Clarity: 8/10 - Some complex logic explained
Reliability: 9/10 - Error cases handled

Learnings:
  • Cache invalidation is tricky
  • TTL-based approach works well

═══════════════════════════════════════════
TASK COMPLETE ✓
═══════════════════════════════════════════
```

---

**Remember**: We optimize for Quality → Clarity → Reliability → Speed
Take the time to do it right. Future you (and your team) will thank you.
