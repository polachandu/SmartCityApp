# Pull Request Review

You are reviewing **Pull Request #{{pr_number}}** in the SmartCityApp repository.

## Linked Issue

**Issue #{{issue_number}}: {{issue_title}}**

{{issue_body}}

## Pull Request

**Title:** {{pr_title}}

**Description:**
{{pr_body}}

**Author:** @{{pr_author}}
**Branch:** `{{head_branch}}` → `{{base_branch}}`

## Commit Messages

{{commit_messages}}

## Files Changed

{{files_changed}}

## Diff

```diff
{{diff}}
```

## Rule Engine Results

The deterministic rule engine has already analyzed this PR:

{{rule_violations}}

## Your Task

Analyze the pull request and provide a structured review:

1. **Does the PR solve the linked issue?** Compare the implementation against the issue requirements.
2. **Is the implementation correct?** Look for bugs, logic errors, and edge cases.
3. **Code quality:** Check for duplicated code, unnecessary changes, and adherence to Java best practices.
4. **Security:** Check for hardcoded credentials, SQL injection risks, and resource leaks.
5. **Performance:** Identify any performance concerns.
6. **Readability:** Assess naming conventions, comments, and code organization.
7. **Rule violations:** Address any violations found by the rule engine above.

Respond with a JSON object matching the required schema.
