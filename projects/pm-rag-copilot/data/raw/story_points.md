# Jira Documentation: Configuring Story Points and Estimation

## What are Story Points?
Story Points are units of measure used by Agile teams to estimate the relative effort, complexity, and risk required to implement a user story or issue.

## How to Configure Story Points in Jira
1. **Enable Estimation Statistic**:
   - Go to **Board Settings** -> **Estimation** tab (requires project admin rights).
   - Under **Estimation Statistic**, select **Story Points** from the dropdown menu (alternatively choose Original Time Estimate or Issue Count).
2. **Ensure Story Points Field is Visible**:
   - Go to **Project Settings** -> **Issue Types**.
   - Select **Story** (or Task/Bug).
   - Check the layout settings to ensure the **Story Points** (or `Story point estimate`) field is added to the issue view screen.

## How to Assign Story Points to an Issue
1. Open any Story or Issue in the Backlog or Board.
2. In the right-side details panel, click on the **Story Points** field.
3. Enter the estimated value (e.g., using Fibonacci scale: 1, 2, 3, 5, 8, 13).
4. Press Enter or save.
5. The story points total will automatically update in your Sprint headers and Velocity Reports.
