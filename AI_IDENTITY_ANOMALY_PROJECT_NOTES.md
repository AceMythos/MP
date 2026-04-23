# AI-Based Identity Anomaly Detection System - Project Notes

Date: 2026-04-23

## Source Material Reviewed

We reviewed the PDF deck:

`/home/igris/Downloads/MAJOR PROJECT PPT_20260416_135448_0000.pdf`

The deck describes an **AI-Based Identity Anomaly Detection System** for detecting identity-based cyber threats using authentication and authorization logs. It proposes UEBA-style behavior analysis, anomaly detection models, risk scoring, and an interactive dashboard.

## Initial Deck Summary

The project idea is to detect suspicious identity behavior such as:

- Account takeover
- Insider threats
- Privilege abuse
- Compromised credentials
- Unusual login behavior
- Device changes
- Country/location transitions
- Failed-then-success login patterns
- Night-time access

The presentation proposed multiple ML models:

- Isolation Forest
- One-Class SVM
- Local Outlier Factor
- Elliptic Envelope

It also proposed an interactive dashboard for alert visualization and anomaly tracking.

## Grill-Me Review Findings

We used the `grill-me` skill to pressure-test the idea before building.

The main risks identified were:

- The project claimed "real-time" detection without a clearly defined live log source.
- The original scope was too broad for a first version.
- "Reduce false positives" was claimed without metrics, baseline data, or evaluation strategy.
- "Explainable outputs" needed a concrete design, not just a claim.
- Identity and network logs may contain sensitive data, so privacy and auditability matter.
- Auto-blocking users is risky and should not be included in the first version.
- Several literature survey items were not directly focused on identity anomaly detection.

The result of the review was: **borderline**.

The concept is strong, but the first version must be narrowed into a defensible, buildable MVP.

## Clarified User Decisions

The project direction was clarified as follows:

1. The first version will run locally on the laptop.
2. Data source order:
   - First: CSV upload
   - Second: synthetic UEBA-style data
   - Later: live Linux or Windows logs
3. The system should support both identity and network-style UEBA fields.
4. The dashboard should look like an enterprise SOC/security command center.
5. The UI should be smooth, informative, easy to navigate, and visually impressive.
6. The system should alert the admin at first, not automatically block users.
7. The project does not need to follow the presentation exactly.
8. The user is a beginner and wants a guided baseline instead of trying to build everything blindly.

## Data Fields Discussed

The UEBA dataset may contain fields such as:

- account
- group
- ip
- url
- port
- vlan
- switch_ip
- time

We decided that the system should normalize these into an internal event schema.

Recommended normalized event schema:

```txt
event_id
timestamp
account
group
source_ip
destination_ip
url
port
vlan
switch_ip
device
country
action
status
resource
raw_source
```

Some fields may be missing depending on the dataset. The system should preserve raw input while normalizing what it can.

## Architecture Direction

The target is an enterprise-shaped local system, not a toy script.

Recommended stack:

- Backend: FastAPI
- ML/data processing: pandas, scikit-learn
- Database: SQLite first, PostgreSQL later
- Frontend: React + Vite
- Styling: Tailwind CSS, enterprise dark SOC-style dashboard
- Charts: Recharts or ECharts

## Core Version 1 Scope

The agreed v1 should include:

- Local admin login
- CSV upload
- CSV field normalization
- Event storage
- Feature engineering
- Rule-based detection signals
- Isolation Forest anomaly detection
- Risk score from 0 to 100
- Severity labels: Low, Medium, High, Critical
- Explainable reason codes
- Alert dashboard
- User risk view
- Anomaly table
- Basic admin audit log

## Admin Login Decision

We decided to include basic admin login in v1.

The v1 login should include:

- One local admin account
- Login page
- Hashed password storage
- Session or JWT-based auth
- Protected dashboard routes
- Audit log for admin actions

We will not add these in v1:

- SSO
- LDAP
- Okta
- MFA
- Full RBAC
- Enterprise identity provider integration

Those are later-stage enterprise features.

## Detection Strategy

The first version should use hybrid detection:

1. Rule-based signals for clear explainability.
2. ML anomaly score for hidden behavior patterns.
3. Final risk score combining rule results and ML output.

Initial real-world detection types:

- New device for user
- New source IP or country
- Impossible travel or rapid location change
- Failed login burst followed by success
- Login outside normal user hours
- Access to unusual URL/resource
- Unusual port or VLAN for account/group
- Group or privilege change event, if available
- User behavior different from their own history
- User behavior different from peer group or global baseline

## Baseline Strategy

We decided both global and per-user baselines are useful, but should be staged:

1. Global baseline first:
   - Detect events unusual compared to all users.

2. Per-user baseline second:
   - Detect events unusual for a specific user.

3. Group baseline third:
   - Detect behavior unusual for a user's group, role, or peer class.

Per-user baselines need enough historical data. If a user has very few events, global or group baselines are safer.

## Metrics To Use

We should avoid relying only on generic "accuracy" because anomaly detection is usually imbalanced.

Better metrics:

- False positive rate per 1,000 events
- Precision at top alerts
- Recall on injected or synthetic attacks
- Mean time to detection
- Alert explainability rate

## Explicit Non-Goals For V1

The first version should not include:

- Automatic user blocking
- Production deployment
- Enterprise SSO
- Full SIEM integration
- Full Windows Event Log support
- Full Linux auth log streaming
- Four-model ML ensemble
- Advanced RBAC
- Cloud deployment

These can be added later after the core detection pipeline works.

## Recommended First Build Milestone

The first implementation milestone should be:

**CSV upload -> normalized events -> feature engineering -> rules + Isolation Forest -> risk scoring -> admin dashboard**

This gives the project a serious foundation while keeping the first build achievable.

## Current Verdict

The project is viable if we build it in stages.

Current status: **ready for baseline architecture and implementation planning**.

The next step is to create the local project structure and implement the v1 baseline.
