package org.hle.clientmockserver.job;

import lombok.Getter;
import lombok.SneakyThrows;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Getter
public class LongRunJob {
    private final long sleepMs;

    private boolean isCompleted;

    public LongRunJob(long sleepMs) {
        this.sleepMs = sleepMs;
    }

    @SneakyThrows
    public void longRun() {
        log.info("LongRunJob start");
        isCompleted = false;
        Thread.sleep(sleepMs);
        isCompleted = true;
        log.info("LongRunJob end");
    }

}
