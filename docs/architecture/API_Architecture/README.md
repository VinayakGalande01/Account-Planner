# API Architecture Documentation Guide

This folder contains the visual API contract specifications for the APEX Account Planner. Because visual schemas (PNG files) are static, this guide explains how they relate to the running codebase and how to regenerate/update them.

---

## 1. Current State vs. Visual Diagrams

1. **REST API Spec (`OpenAPI 3.0 REST API Specification.png`):**
   * Represents the endpoint routes for user auth, chat query execution, and database syncing.
   * **Active Codebase Spec:** The current live specification is saved as [openapi.json](./openapi.json) in this directory. It was exported directly from the FastAPI application schema.
2. **GraphQL Spec (`GraphQL API Schema.png`):**
   * Represents the **target-state** schema design for advanced dashboards and analytical widgets.
   * **Active Codebase Spec:** The active running codebase does *not* expose a GraphQL server (no GraphQL packages are installed in the backend's dependencies). It relies entirely on the FastAPI REST endpoints.

---

## 2. How to Export and Update the REST API Spec

If you modify API routes, parameter schemas, or data structures in `backend/main.py` or the `backend/api` directories, you can export a fresh spec file:

### Step 1: Run the Export Script
From the `backend/` directory, execute the utility exporter script:
```bash
cd backend
python export_openapi.py
```
This runs the FastAPI app initialization cycle and exports a fresh JSON spec file directly to this folder as `documentation/API_Architecture/openapi.json`.

### Step 2: Convert/View in Swagger or ReDoc
You can import the generated [openapi.json](./openapi.json) file into:
* **[Swagger Editor](https://editor.swagger.io/):** For interactive testing, editing, or converting the JSON schema into YAML format.
* **[ReDocly](https://redocly.github.io/redoc/):** For clean, side-by-side three-column documentation pages.

---

## 3. How to Regenerate Visual Schema Diagrams

To update the `.png` visual diagrams to match the new spec:
1. **Using Swagger Editor:** Import your JSON/YAML, select `Generate Client` or take a high-resolution snapshot of the generated endpoint lists.
2. **Using Mermaid.js / PlantUML:** You can map the endpoints into a sequence flow chart or class schema using text-based diagramming tools and render them to PNG.
3. **Using GraphQL Visualizers (Target State):** If GraphQL is implemented in a future phase, you can run introspection queries against the GraphQL endpoint and paste the schema into [GraphQL Voyager](https://apis.guru/graphql-voyager/) or [GraphQL Visualizer](https://graphql-kit.com/graphql-voyager/) to generate a fresh interactive schema layout.
