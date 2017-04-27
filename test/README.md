# Manual Tests

1. Enable Broker

```
$ node broker.js
```

2. Enable IP Camera Agent

Camera agent gets (HTTP Get) a snapshot from IP camera, and publishes
the received body to event notifier.

```
$ node camera.js
```

3. Enable Event Notifier

Event notifier gets the latest camera snapshots and sends a
notification (via email) to user.

```
$ node mail.js <sender-mail-address> <sender-mail-password> \
    <receiver-mail-address>
```

4. Send Simulated Event

```
$ mosquitto_pub -h localhost -t dt42/camera -m snapshot
```
