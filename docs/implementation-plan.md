# aiagent Implementation Plan

## Target Window

Complete the first usable version within 6 weeks.

## Module Build Order

1. Core project config and schemas
2. Orchestrator and shared state
3. LLM service and persona pipeline
4. WebSocket and chat input path
5. TTS output path
6. ASR input path
7. Memory system
8. Live2D output path
9. Bilibili and OBS integrations
10. RAG and knowledge pipeline
11. Web control panel
12. Integration testing and stabilization

## 6-Week Schedule

### Week 1

- Finalize schemas, config, and runtime bootstrap
- Build orchestrator skeleton
- Build LLM facade and response planner skeleton

### Week 2

- Build persona loader and style rewriter
- Connect chat input to response generation
- Define output packet format

### Week 3

- Build TTS dispatcher and output broadcaster
- Add speaking state and interrupt rules
- Deliver first text-to-voice loop

### Week 4

- Build ASR listener
- Add short-term memory and user profile memory
- Connect memory recall into context builder

### Week 5

- Build Live2D dispatcher and motion policy
- Add Bilibili and OBS integration shells
- Build basic dashboard pages in web app

### Week 6

- Build RAG skeleton and document pipeline
- Run integration testing
- Fix reliability issues and freeze v0.1 scope

## Delivery Milestones

- End of Week 2: text chat agent with persona rewriting
- End of Week 3: chat agent can speak through TTS
- End of Week 4: voice input and memory loop working
- End of Week 5: avatar and stream integrations connected
- End of Week 6: first integrated streamer runtime ready
