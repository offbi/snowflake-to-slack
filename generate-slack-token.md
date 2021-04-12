# Generate Slack Token with Slack App


## 1. Create New Slack App

Goto [https://api.slack.com/apps](https://api.slack.com/apps) and click on the **Create New App** button to create a new slack application.

![Create app](https://github.com/offbi/snowflake-to-slack/blob/main/.github/imgs/1-new-app.png?raw=true)

In the next popup add a new **App Name** and select the **Slack Workspace** and click on the **Create App** button

![Add app name](https://github.com/offbi/snowflake-to-slack/blob/main/.github/imgs/2-create-slack-app.png?raw=true)

## 2. Select the Token Scopes

Once the application is created in the **Add features and functionality** section click on the **Permissions** button to set the token scopes

![Click on permissions](https://github.com/offbi/snowflake-to-slack/blob/main/.github/imgs/3-permissions.png?raw=true)

Under **User Token Scopes** select the following scopes
* **chat:write** - Send messages as app
* **chat:write.public** - Send messages to channel the app is not member of
* **im:write** - Start direct messages with people
* **mpim:write** - Start group direct messages with people
* **groups:write** - Manage private channels that app has been added to and create new ones


![Select token scopes](https://github.com/offbi/snowflake-to-slack/blob/main/.github/imgs/4-scopes.png?raw=true)


## 3. Install the Application in the Workspace

Next step is to install the application in the desired workspace and allow access to the requested scopes. Click on the  **Install App to Workspace** button

![Install app to workspace](https://github.com/offbi/snowflake-to-slack/blob/main/.github/imgs/5-install.png?raw=true)

Then on the concent screen click on **Allow** button to give the necessary permissions.

## 4. Copy OAuth Access Token & Use in Azure Pipelines

Finally, copy the **OAuth Access Token** and use it in the **Slack API Token** field.

![Copy the access token](https://github.com/offbi/snowflake-to-slack/blob/main/.github/imgs/6-token.png?raw=true)
