# AI Next.js + Sanity Web App Builder

## Overview
**AI Next.js + Sanity Web App Builder** is a Python-based system that automatically generates production-ready web applications built on **Next.js** and **Sanity CMS**, directly from **Figma designs** and guided by **AI-driven code generation**.  

The system transforms design into working code — setting up everything from the initial boilerplate to the fully connected frontend and CMS structure.

---

## Core Objectives
- Automate setup of a **Next.js + Sanity** project, including environment configuration, Git initialization, and documentation.
- Convert **Figma design data** into structured, reusable code components through AI.
- Generate complete schema definitions, GROQ queries, TypeScript interfaces, and React components for each design element.
- Assemble all generated components into functional pages with routing, preview, and sitemap integration.

---

## Project Architecture

### 1. Automated Project Generation
The system uses the **official Sanity Next.js Clean template** to create a production-ready environment.

**Template Source:** [sanity-io/sanity-template-nextjs-clean](https://www.sanity.io/templates/nextjs-sanity-clean)

The template provides:
- **Next.js 16** with App Router for optimal performance
- **Sanity Studio** with Visual Editing capabilities
- **Live Content API** for real-time content updates without rebuilds
- **Presentation Tool** for live preview and editing
- Pre-configured schema (Page, Post, Person, Settings)
- Drag-and-drop page builder with visual editing
- Automatic environment configuration
- Integrated Unsplash support for media

**Setup Command:**
```bash
python -m project_init.main
```

This command:
1. Checks Sanity CLI authentication (prompts login if needed)
2. Runs `npm create sanity@latest -- --template sanity-io/sanity-template-nextjs-clean`
3. Extracts project configuration automatically
4. Provides clear next steps and documentation links

The output is a fully functional, production-ready project with Visual Editing, Live Content API, and best practices built-in.

---

### 2. Figma Integration and Design Parsing
Through the **Figma API**, the builder retrieves structured representations of a web design.  
This step involves:

- Connecting to a specified Figma design file using an API key or file ID.  
- Extracting all components, frames, and text data.  
- Storing that information in a local **SQLite database**.  
- Organizing metadata (e.g., hierarchy, component type, style references, texts, colors, and spatial data).

This database becomes the foundation for AI-based component generation and code mapping.

---

### 3. AI-Driven Component Generation
Each design component extracted from Figma is assigned to an **AI worker** that processes it independently and in parallel.  

Each AI worker performs these actions:
- Analyzes design data and metadata from the SQLite database.  
- Generates:
  - A **Sanity schema** (content type) for that component.  
  - A **GROQ query** corresponding to the schema for data retrieval in Next.js.  
  - A **TypeScript interface** for component props.  
  - A **React component** that uses the data to render the UI.  
- Iteratively improves results using feedback:
  - Figma component screenshot comparisons.  
  - Perceptual hashing for visual consistency checks.  
  - Browser-rendered visuals and log-based QA feedback.  
- Rewrites and refines until the result matches the intended design with high fidelity.

Each AI worker operates within an isolated **branch or worktree**, allowing safe parallel development and later merging of components.

---

### 4. Assembly and Sitemap Creation
After all components are generated and validated, the builder:
- Assembles components into complete **Next.js pages**.  
- Links page structures according to design-defined navigation hierarchies.  
- Connects Sanity datasets with page queries dynamically.  
- Generates:
  - **Sitemaps** for search optimization.  
  - **Routing configurations** for Next.js.  
  - Optional metadata files (SEO, Open Graph, structured data).

The end result is a cohesive, CMS-connected web app ready for deployment.

---

## Vision and Goals
The **AI Next.js + Sanity Web App Builder** aims to redefine the design-to-code process by fully automating the repetitive and complex steps of web development.  

Key goals:
- Minimize manual setup and configuration time.  
- Create seamless collaboration loops between designers, developers, and AI.  
- Enable AIs to continuously improve the accuracy of visual and data alignment.  

Ultimately, the system seeks to turn design prototypes into production-grade codebases through intelligent automation.

---

## Current Status
Project phase: **Active Development**  

**Completed:**
- ✅ Automated project setup using official Sanity Next.js Clean template
- ✅ Visual Editing and Live Content API integration
- ✅ Figma data extraction pipeline

**In Progress:**
- 🔄 AI worker orchestration for component generation
- 🔄 Component validation and refinement system

**Next Steps:**
- Assembly and page generation
- Sitemap and routing automation

---

## Future Directions
Potential areas of expansion and improvement:
- Support for other design platforms (e.g., Adobe XD, Sketch).  
- Integration with cloud deployment tools (e.g., Vercel, Netlify).  
- Advanced AI aesthetic evaluation and UX-aware correction.  
- Human-in-the-loop feedback for fine-tuning AI-generated components.  
- Shared workspace interfaces for developers, designers, and AIs.

---

## Summary
**AI Next.js + Sanity Web App Builder** provides a structured, automated approach to generating web applications directly from design assets, merging Figma, AI, and modern web development.  
It represents an evolving framework for **intelligent, self-improving web generation pipelines**, bridging creative design and high-quality code delivery.

---
