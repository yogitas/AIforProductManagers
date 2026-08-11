# Jira Documentation: Creating Jira Automations

## What is Jira Automation?
Jira Automation allows teams to automate repetitive tasks and processes without writing code using a simple `WHEN` (Trigger) -> `IF` (Condition) -> `THEN` (Action) rule builder.

## How to Create a Jira Automation Rule
1. Open your Jira project and navigate to **Project Settings** -> **Automation** (or Jira Settings -> System -> Automation for global rules).
2. Click **Create Rule** in the top right corner.
3. **Select a Trigger (WHEN)**:
   - Choose what event fires the rule (e.g., `Issue Created`, `Issue Transitioned`, `Field Value Changed`, or `Scheduled`).
   - Click **Save**.
4. **Add Conditions (IF)** (Optional):
   - Click **+ Add Component** -> **Condition**.
   - Select criteria (e.g., `Issue Fields Condition` where Issue Type = Story and Priority = High).
   - Click **Save**.
5. **Add Actions (THEN)**:
   - Click **+ Add Component** -> **Action**.
   - Choose the automated task (e.g., `Assign Issue`, `Send Slack Notification`, `Add Comment`, or `Transition Issue`).
   - Fill in action parameters and click **Save**.
6. **Name and Turn On**:
   - Give your automation rule a descriptive name (e.g., "Auto-assign High Priority Bugs").
   - Click **Turn It On** to activate the rule immediately.
