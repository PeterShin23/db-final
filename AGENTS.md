# Databricks POC and Presentation around Business Scenario

## Overview

This project is meant to take the provided business scenario and do the following:

1. Build the smallest Databricks Free Edition prototype that proves a useful business outcome.
2. Present it like a pre-sales Solutions Engineer: start with the customer's problem, show the working proof, and tie every technical choice back to value.

## Scenario Breakdown

When a scenario arrives, the AI agent should:

1. Identify the customer, stakeholder, decision to support, and business pain in plain language.
2. Extract the available data, missing data, assumptions, constraints, and success metric.
3. Choose one demoable workflow that answers the business decision; skip side quests.
4. Map the workflow to Databricks capabilities only where they matter: ingestion, SQL/analytics, AI/ML, governance, dashboards, or app/demo surface.
5. Create mock data only if needed, and make it realistic enough to show the decision clearly.
6. Build a thin end-to-end POC: data in, transformation/analysis, insight out, visual/app/demo.
7. Prepare the talk track around: problem, definitions, scope, prototype, business value, limits, tradeoffs and why we went with certain decisions over others, and next steps.
8. Be explicit about what is real, mocked, unfinished, and what a production version would require.

For the purposes of this interview:

1. Understand the business problem.
2. Build a small technical proof.
3. Explain why the technical proof matters to the business.
4. Explain how Databricks fits into the future production version.

## Project Structure

`/poc` is the directory where the POC will be built. This POC must run on the Databricks free tier platform. This directory must have clean structure.

1. Any mock data files will go in here under `data/`.
2. Any notebooks to be run should go under `notebooks` and be prefixed with a number to indicate order of run in the Databricks notebooks.
3. Any code that will land for the visual aspect of the project should go in `app`
4. What would be nice is that there's a button that's clickable that shows a full page pop-up with a close button of the architecture of how Databricks is going to be used (data flowing in, transformed, and how it's going to be used, ideally we also use databricks svg/img assets as well) AND the medallion architecture of what the data looks like at each step.

`/poc-example` is an example directory of an app I made as a test run. It's not perfect, but it gives you an idea of what I want.

---

`/presentation` is the directory where an HTML/CSS/Javascript presentation slide deck should be. The presentation should be nice without going overboard. The people listening to the presentation may include non-technical stakeholders so avoid jargon that's too technical, and if the jargon is necessary then we must define it. Keep in-slide animations simple and apply when it drives home the point. No transitions from slide-to-slide. The transitions should work with arrow keys. Run it on localhost:3002.

Presentation should include the following slide format

1. Title slide
2. Business Problem
3. Definitions
4. Prototype scope
5. Business Value
6. Next Steps

## Copy-Pasted Business Scenario
