# High-level system goal

A user-friendly, self-hosted platform that:

- Abstracts infrastructure complexity
- Leverages existing packaging ecosystems to deploy a wide range of applications for non technical users
- Enables peer-to-peer federation for resilience and availability
- Enables peer-to-peer private sharing of resources, compute and federated deployment of tools/apps otherwise too expensive to run on your own

## 1. Core Functional Requirements
### 1.1 Application lifecycle management

The system must:

- Install, update, rollback, and remove applications
- Support declarative desired state
- Track versions and dependencies
- Handle configuration + secrets cleanly
- Manage discoverability + access through RBAC

Implication:
You need a unified app definition format that can map to:

- Docker Compose / OCI images
- Nix derivations
- Helm charts (optional)
- Ray jobs

App = declarative spec


### 1.2 Multi-runtime support (pluggable execution backends)

The system should support:

- Containers (OCI/Docker/Podman)
- Orchestrators (Kubernetes)
- (Optional) Native packages (NixOS)
- Ray (or any drop in parallelization framework)
- Gvisor and safe code execution platforms

The system should prioritize security when choosing a backend.

Requirement:
A runtime interface layer, e.g.:

```
app:
  name: nextcloud
  runtime: container | nix | helm
  spec: ...
```


### 1.3 Persistent storage abstraction

You need a storage layer independent of runtime:

- Pools
- Volumes
- Backups
- Replication across peers

Must support:

- Local storage
- Distributed storage (eventually)
- RBAC + encryption on logical/volume level
- Compute parallelization (not necessarily embarassingly parallel, Phase 4)
- Telemetry for uptime reliability

Key requirement:

Apps declare storage needs:
```
storage:
  - name: data
    size: 10Gi
    replication: optional|required
```

But storage also must be able to be accessed directly:

```
cep storage volume show data
```


### 1.4 Networking & service discovery

- Zero-config networking between nodes
- Service naming (e.g., nextcloud.cepnet)
- Secure peer-to-peer connectivity
- Peer validation

We already identified Nebula, which is a strong fit.

Requirement:

- Built-in overlay network abstraction
- Service discovery across servers
- No manual port forwarding


### 1.5 Identity, trust, and federation

The system must:

- Allow nodes to form trusted clusters (“social federation”)
- Share resources (compute/storage)
- Enforce trust boundaries
- Allow secure invite based joining

Key capabilities:

- Node identity (cryptographic)
- Trust relationships (friends, groups)
- Access control policies
- Users can use network layer identity to authenticate on the application level (Similar to f.i. Zscaler <> Entra federation)

“I trust my brother’s server for backups”
“I don’t trust it to run my workloads”
"I trust my mom's server for music backup, but not the homework folder"


### 1.6 High availability & failover
- Automatic failover between trusted nodes
- Health checks
- Service migration

Requirement:

Apps can declare HA level:
```
availability:
  mode: single | replicated | failover

```


### 1.7 UX abstraction layer

This is the hardest requirement.

You need:

- App store–like experience
- Visual system status
- One-click deploy
- Clear mental model (no infra jargon)

Users should never see:

- containers
- pods
- volumes
- overlay networks



## 2. Non-Functional Requirements
### 2.1 Simplicity first
- Must work on one server + client with minimal setup
- Federation is opt-in, not required


### 2.2 Offline-first capability
- System should function without internet
- Federation should degrade gracefully


### 2.3 Security by default
- Encrypted communication
- Minimal exposed surface
- Automatic updates (with control)


### 2.4 Deployment modularity
Should run on:
- Preconfigured device (Some ootb solution)
- Flashed onto rpi like devices
- Custom installation script for unix


### 2.5 Extensibility
Plugin system for:
- New runtimes
- Storage backends
- Networking layers



## 3. Packaging Ecosystem Requirements
### 3.1 Unified application spec (critical)

You need a translation layer:

Ecosystem	Mapping
Docker/OCI	Native
Nix	Wrapped
Helm	Optional adapter

Should define:
AppSpec → Adapter → Runtime


### 3.2 Reuse existing ecosystems

Must support:

- OCI registries
- Helm charts
- Git-based configs
- Nixpkgs (if needed)



## 4. Resource sharing model

Nodes must be able to share:

- Storage
- Compute


## 5. Observability & Control
- Logs per app
- System health overview
- Federation status
- Resource usage
- Uptime/Reliability of shared users (maps to phase 4 for uptime incentives)



# Development phases
## Phase 1 (MVP)
- OCI containers + Compose-like abstraction
- Nebula networking
- Simple AppSpec
- Single-node + basic network federation
- trust + identity
- auth integration
- Extensive test coverage
- Baseline build + integration pipeline


## Phase 2
Introduce:
- Distributed storage layer
- Distributed compute layer
- Kubernetes
- HA primitives


## Phase 3
- UX 
- Rollout to friends
- Gather feedback
