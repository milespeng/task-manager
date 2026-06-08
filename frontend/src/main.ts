/**
 * 应用入口
 * 功能描述：创建 Vue 应用，注册 Element Plus、Router、Pinia
 */
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(ElementPlus, { locale: zhCn })
app.use(router)

app.mount('#app')
