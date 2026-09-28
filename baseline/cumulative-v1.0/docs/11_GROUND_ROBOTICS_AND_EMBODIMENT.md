# Ground robotics, manipulation and new embodiments

Drones remain in scope, but not every useful action needs flight. A slow ground platform can be an interface, a sensor carrier, a communications relay or a carrier of light objects. A desktop arm can support experimental handling. These are proposed branches whose hazards and utility must be measured separately.

## First useful actions

Investigate telepresence, repositioning a camera/sensor between marked locations, moving a communications node within an approved area, bringing an inert lightweight kit or phone, and manipulating low-risk test objects on a bench. The first task should have a clear completion observable from sensors or an operator, not “the model thinks it finished.”

Do not start with human lifting, hot cooking, sharp tools, medical administration, stairs or arbitrary door opening. Lack of permission or safe operating space should pause a particular task, not make the entire robotics research useless. A desktop bench with dummy objects can validate much of the interaction and control architecture.

## Learning from existing platforms

R07 (Mobile ALOHA), R08 (SO-101), R09 (LeKiwi), R10 (openpi) and R11 (restricted-access robotics models) give different precedents: demonstrations, printable hardware, open policies and emerging local action models. These are not interchangeable levels of readiness. A model expecting one camera/action convention cannot simply be attached to another arm.

Build-versus-buy evaluation must include mechanical assembly, actuators, controller, cabling, power, camera placement, calibration, stop mechanism, spares and operator time. Printed parts alone do not make a complete platform. An integrator-assembled development unit may be better value than the cheapest unfinished kit; do not decide without the complete bill of materials.

## Control architecture

Natural-language intent selects a bounded skill or asks for clarification. A skill planner produces constraints and an execution proposal. A deterministic controller checks the calibrated hardware and approved workspace, owns command timing, and limits motion independently of the language model. Keep stop/recovery accessible to an operator even if the UI or network stalls.

Describe the actual safe state for each device. A rover may stop and hold; a manipulator holding an object may need controlled support; a drone cannot universally shut down motors. A global conversational “stop” routes to a defined domain recovery request, not an arbitrary power cut.

Never stream unconstrained LLM motor commands. A learned visual-action policy is also untrusted until qualified; inference close to the hardware does not remove control limits. Record policy version, observations, action space, calibration, rate, bounds and observed termination conditions.

## Progression

**B0:** mock robot adapter and recorded observations. **B1:** manual teleoperation in an empty controlled area with physical stop verified. **B2:** record repeatable demonstrations and ground-truth outcomes. **B3:** execute a fixed bounded skill under supervision. **B4:** evaluate learned variants on held-out placements while preserving independent limits. **B5:** allow a reviewed standing task policy for a small set of qualified routines. **B6:** coordinate mobile sensing or manipulation with the assistant's active-perception/engineering loop.

Each step has different data and validation needs. Failures count; exclude cherry-picked successful clips as primary evidence. A novel environment or changed tool/fixture may require requalification. Do not claim generality from one tabletop layout.

## Physical and human factors

Define workspace boundaries, people/pet exclusion, speed/force/energy limits set from competent hardware review, pinch/drop hazards, emergency stop, stable power and operator position. A printed end effector or new payload changes risk and calibration. Verify manual recovery when sensing, network, policy or actuator feedback is missing.

A household robot also needs social permission: no entering private spaces or pointing a camera at someone because the primary owner requested it. Account for shared rooms and guest consent. Lack of a face-identification feature does not eliminate privacy risks.

## Advanced research leads

Perching, multimodal locomotion, event cameras, tactile feedback, compliant/soft manipulation, semantic navigation and multi-robot exploration may offer value. They are research leads, not selected dependencies or verified capabilities in this bundle. H12 must locate specific primary papers/code and H10 must define a relevant, safe replication task before prioritizing them.

Use the research atlas to extract design lessons: modular sensing, uncertainty-aware navigation, demonstration data, graceful recovery and measured resource use. Do not chase extreme speed or force as a proxy for household usefulness.

## Integration gate

Every accepted skill exposes a typed capability with exact prerequisites, allowed objects/regions, expected observation, timeout, cancellation, unknown-outcome handling and qualification revision. The shared assistant may propose it, but only the robotics executor has the device interface. A capability can be temporarily unavailable without erasing the user's original requirement.
