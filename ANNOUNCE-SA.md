### Minor release 1.42.0 is scheduled for 9/10/2021 between 6:00pm and 11pm CST

This release adds the following:
* OFFLINE transcription now uses ffmpeg to transcode audio - see [the list of supported audio formats](https://support.voicegain.ai/hc/en-us/articles/360050477331-Supported-Audio-Formats)
* Edge Deployment UI now shows all available versions and allows deployment of any one of them onto an Edge Cluster. Version rollback is also possible using this feature.
* data-api has been split off from the web-api - this improves robustness of the platform 
* Digit formatter has been added to transcript returned from polling real-time transcription session
* In the Cloud, added ability to increase data persistence time for individual accounts. In the past persistence was capped at 7 days.

Edge specific notes:
* data-api has been split off from web-api - it is recommended that you Rebuild to this version if you are doing a lot of audio file uploads. Overloading data-api with too many concurrent large file uploads will not longer affect speech recognition sessions in progress.

**Backwards incompatibility**:
* We have changed the `result.incrementalTranscript` field in the response from `GET  https://api.voicegain.ai/v1/asr/transcribe/{sessionId}` - the new design will better support the changing hypotheses, in particular in commbination with digit and other formatters.

This release fixes the following issues:
* #rcj-339: v1/asr/transcribe/{}/transcript?format=text API does not behave like spec w/o interval parameter
* #rcj-338: Exception in data-api when upload multiple files concurrently on Edge

### Minor release 1.41.0 is scheduled for 8/27/2021 between 6:00pm and 11pm CST

This release adds the following:
* MRCP server's 3rd-party dependencies get updated to their latest versions
* Offline transcription tasks get optimized to increase the throughput
* Ability to enable digit formatting as default for a Context
* Ability to enable audio capture for all transcriptions in a Context 
























 












































