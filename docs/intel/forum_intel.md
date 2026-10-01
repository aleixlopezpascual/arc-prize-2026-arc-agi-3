# Forum Discussions & Community Intel: arc-prize-2026-arc-agi-3

| ID | Title | Votes | Comments | Date |
| :--- | :--- | :--- | :--- | :--- |
| 695158 | Upgraded accelerators | 20 | 2 | 2026-04-28 18:20:14.975000 |
| 697944 | Update on Code Requirements | 11 | 7 | 2026-05-07 22:16:59.523000 |
| 697720 | Update on accelerators | 9 | 6 | 2026-05-07 02:12:48.865000 |
| 684625 | How to get started + Competition's Official Discord | 8 | 9 | 2026-03-25 16:40:49.697000 |
| 687384 | Welcome to ARC Prize 2026 - ARC-AGI-3 Edition | 7 | 0 | 2026-04-02 22:37:13.554000 |
| 713634 | Clarification on deadline for milestone prizes | 5 | 5 | 2026-06-24 20:36:05.362000 |
| 705405 | Correcting an Error in Competition Submission Limits | 3 | 12 | 2026-06-09 21:39:16.349000 |
| 717133 | Tufa Labs’ Winning Solution for ARC-AGI-3 Milestone 1 | 71 | 18 | 2026-07-01 14:47:58.064000 |
| 686416 | Simplified submission framework | 41 | 3 | 2026-03-31 07:29:19.755000 |
| 742801 | We will not be open-sourcing for the second milestone prize | 38 | 42 | 2026-09-23 15:16:10.913000 |
| 716696 | Code for milestone 1st place open sourced - writeup tomorrow | 38 | 16 | 2026-06-30 21:10:43.953000 |
| 744792 | Comparing the Milestone 2 winning solutions | 37 | 14 | 2026-10-01 00:36:37.030000 |
| 691696 | It is 0.66% | 24 | 8 | 2026-04-15 15:37:57.379000 |
| 709355 | View your run time and the historical leaderboard | 23 | 5 | 2026-06-18 11:04:47.252000 |
| 687648 | ARC3 Offline Agent Evaluation and Recording Viewer | 23 | 10 | 2026-04-03 11:22:40.455000 |
| 705043 | Exact timing of milestone prize | 21 | 7 | 2026-06-08 14:16:26.896000 |
| 687655 | Human scores visible to agents | 20 | 3 | 2026-04-03 11:42:35.751000 |
| 742148 | Long Queue for RTX Pro 6000 (8 hours) partially due to abusive used for non ARC-AGI-3 tasks, Proposal to mitigate | 20 | 22 | 2026-09-20 09:41:10.344000 |
| 739938 | What Have You Tried So Far? | 18 | 6 | 2026-09-07 08:41:20.032000 |
| 703426 | I did "autoresearch" in a hackathon and won some GPU credits | 15 | 4 | 2026-05-31 04:54:54.847000 |

## High-Value Technical Discussions

### Topic 687648: ARC3 Offline Agent Evaluation and Recording Viewer

<p>Hi everyone, sharing a reproducible ARC3 notebook for offline agent evaluation and debugging.</p>
<p>Notebook: <a href="https://www.kaggle.com/code/shiinehata/arc3-agent-evaluation-and-recording-viewer/notebook?scriptVersionId=308657447" target="_blank">ARC3 Offline Agent Evaluation and Recording Viewer</a></p>
<p>What this notebook adds:</p>
<ul>
<li>Runs the copied agent offline</li>
<li>Computes per-game action-count and score stats on public games</li>
<li>Visualizes recordings for behavior inspection and debugging</li>
</ul>
<p><strong>Key point: The pipeline runs through the official main.py command path, so behavior is closer to the real evaluation runtime than using a custom simulator from environment files</strong></p>
<p>Run artifacts:</p>
<ul>
<li>recordings</li>
<li>summary.csv</li>
<li>summary.txt</li>
<li>scorecard.json</li>
<li>run.log</li>
</ul>
<p>Visualization snapshots:
<img src="https://www.googleapis.com/download/storage/v1/b/kaggle-forum-message-attachments/o/inbox%2F21018013%2F7e0b217497c67660bd42b2394b87b581%2F1.PNG?generation=1775215264186395&amp;alt=media" alt=""></p>
<p><img src="https://www.googleapis.com/download/storage/v1/b/kaggle-forum-message-attachments/o/inbox%2F21018013%2F5feffd16267d1fc087971e8779860631%2F2.PNG?generation=1775215276539069&amp;alt=media" alt=""></p>
<p><img src="https://www.googleapis.com/download/storage/v1/b/kaggle-forum-message-attachments/o/inbox%2F21018013%2F14c9262f989966d4d0730b6839cc8ccf%2F3.PNG?generation=1775215287433041&amp;alt=media" alt=""></p>

### Topic 687655: Human scores visible to agents

<p>From some submission probing, I believe that the scores of the second-best human used for scoring (i.e. <code>environment_info.baseline_actions</code>) are available to us for the 110 test games during submission. Is this intentional, and are we indeed free to use this information?</p>
