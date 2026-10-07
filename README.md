# 🚨 LIFEGRID — Event-Driven Disaster Coordination Platform

> A cloud-native emergency coordination platform built with AWS serverless architecture to demonstrate disaster reporting, risk assessment, resource coordination, shortage detection, and event-driven processing.

![LIFEGRID](https://img.shields.io/badge/LIFEGRID-Disaster%20Coordination-blue)
![AWS](https://img.shields.io/badge/AWS-Serverless-orange)
![React](https://img.shields.io/badge/Frontend-React-61DAFB)
![Python](https://img.shields.io/badge/Backend-Python-3776AB)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🌍 Overview

LIFEGRID is a cloud-native disaster coordination platform designed to demonstrate how modern serverless and event-driven architectures can be used to coordinate emergency information.

The platform allows users to:

- Create disaster reports
- Track disaster status
- Assess potential risk
- Detect resource shortages
- Manage available emergency resources
- Process events asynchronously
- Maintain idempotent event processing
- Monitor backend activity through AWS
- Visualize operational information through a web dashboard

LIFEGRID is designed as a **technical demonstration and learning project** focused on AWS cloud architecture, event-driven systems, serverless computing, distributed processing, and resilient application design.

---

## 🎯 Problem Statement

During a disaster, information can arrive from multiple sources and change rapidly.

A coordination system needs to handle:

- Incoming disaster reports
- Risk evaluation
- Resource availability
- Resource shortages
- Status transitions
- Duplicate events
- Asynchronous processing
- Failure handling
- Operational visibility

Traditional tightly coupled applications can become difficult to scale and maintain when multiple workflows need to react to the same event.

LIFEGRID explores an **event-driven serverless approach** where different processing stages can respond to events independently.

---

## 💡 Solution

LIFEGRID separates the system into multiple logical components.

A disaster report enters through an API.

The backend stores the report and publishes an event.

Event-driven processing then performs:

1. Report validation
2. Risk assessment
3. Resource evaluation
4. Shortage detection
5. Status updates
6. Event tracking
7. Idempotency checks

This approach reduces unnecessary coupling between different processing stages.

AWS describes EventBridge as a serverless event bus for connecting application components and building event-driven architectures. :contentReference[oaicite:0]{index=0}

---

# 🏗️ Architecture

```text
                         ┌──────────────────────┐
                         │    LIFEGRID Web UI   │
                         │   React + Tailwind   │
                         └──────────┬───────────┘
                                    │
                                    │ HTTPS
                                    ▼
                         ┌──────────────────────┐
                         │   Amazon API Gateway │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      AWS Lambda      │
                         │   FastAPI / Mangum   │
                         └──────────┬───────────┘
                                    │
                      ┌─────────────┴─────────────┐
                      │                           │
                      ▼                           ▼
             ┌─────────────────┐       ┌─────────────────┐
             │ Amazon DynamoDB  │       │ Amazon          │
             │                 │       │ EventBridge     │
             │ Reports         │       │                 │
             │ Resources       │       │ Event Routing   │
             │ Event Ledgers   │       │ Async Workflow  │
             └─────────────────┘       └────────┬────────┘
                                                │
                              ┌─────────────────┼─────────────────┐
                              │                 │                 │
                              ▼                 ▼                 ▼
                       Risk Processing   Resource Processing  Event Handling
                              │                 │                 │
                              └─────────────────┼─────────────────┘
                                                │
                                                ▼
                                      ┌──────────────────┐
                                      │    DynamoDB      │
                                      │ Updated State    │
                                      └──────────────────┘

                         Monitoring
                              │
                              ▼
                       Amazon CloudWatch

                         Security
                              │
                              ▼
                           AWS IAM
