# 在 Settings 类中添加以下字段
WECHAT_CALLBACK_TOKEN: Optional[str] = Field(default=None, description="企业微信回调Token")
FRONTEND_URL: str = Field(default="http://localhost:3000", description="前端URL")
AI_PROVIDER: str = Field(default="claude", description="默认AI服务提供商")