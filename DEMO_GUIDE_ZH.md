# 现场实时演示提纲

1. 双击 Start Live Demo.command，打开 http://127.0.0.1:8770。这里默认就是实时操作台，不需要经过介绍页面。
2. 保留默认 GEN-009、ChatGPT + Gemini、每款应用执行2次。点 Check readiness，再点 Start real demo。
3. 说明左侧是模拟器当前屏幕，目标每秒5帧；输入、发送和生成都来自真实 Appium 操作。View guarded 表示导航或未验证界面暂时被遮挡，Stream delayed 表示画面更新延迟，不能把它说成正常直播。
4. 右侧显示当前问题和完成验证后采集的回答。切到 Appium HTTP log 展示真实命令、HTTP状态和耗时，再切回 Python events。可以点 Full screen 或 Enlarge live view 放大。
5. 观察同一应用的第1次、第2次独立结果，展示不同 Attempt ID、采集完整性和耗时。随后展示另一款应用的两次实际执行。不要宣称每次一定PASS。
6. 结束后查看4条结果，点击某个 Attempt ID 查看完整问题与回答，再导出本次证据。摄像状态变成 Run finished 后，左侧明确是最后一帧，不是继续直播。
7. 如需模型介绍，打开 3D model & generator 辅助面板，点击实际Python生成器按钮；历史统计从 Recorded library 打开并说明原日期。它们与刚才现场执行分开。

若有阻断或超时，保留原结果。需要停止时点 Stop run，不为了展示更好结果自动重发。历史114条仍为37 PASS、58 REVIEW、19 ERROR；58条人审未签署。现场新结果不能用于覆盖这些记录。

本次交付不重新录制或剪辑视频。直接演示实际页面即可；原有视频和证据包全部保留。
