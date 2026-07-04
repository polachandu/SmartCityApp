# Assignment Intent Detection

Analyze the following comment on **Issue #{{issue_number}}: {{issue_title}}** to determine if the commenter is requesting to be assigned to this issue.

## Comment

**Author:** @{{comment_author}}

> {{comment_body}}

## Known Trigger Phrases

The following phrases indicate an assignment request:
{{trigger_phrases}}

## Your Task

Determine if the comment is requesting assignment. The comment doesn't need to match a trigger phrase exactly — understand the **intent**.

Respond with a JSON object:

```json
{
  "should_assign": true | false,
  "reason": "Brief explanation of why this is or isn't an assignment request"
}
```
