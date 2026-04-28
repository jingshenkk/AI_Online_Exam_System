<template>
  <div class="main">
    <div class="login-main-box">
      <div class="login-left-box">
        <div class="left-content">
          <h1 class="left-title">智能评分考试系统</h1>
          <p class="left-subtitle">让考试评分更智能、更高效</p>
          <ul class="left-features">
            <li>AI 智能评分，让工作更轻松</li>
            <li>多维度分析，让教学更精准</li>
            <li>安全稳定，让考试更放心</li>
          </ul>
        </div>
      </div>
      <div class="login-right-box">
        <div class="login-right-common login-right-logo-box">
          <div class="logo-content">
            <span class="logo-wording-item">智能评分考试系统</span>
          </div>
        </div>
        <div class="login-right-common login-right-form-box">
          <span class="form-title-wording">欢迎登录</span>
          <div class="login-select-role-group" v-if="!isAdministrator">
            <div class="select-role-item select-active-item" @click="handleActiveStudent">学生</div>
            <div class="select-role-item" style="padding-left:20px;" @click="handleActiveTeacher">教师</div>
          </div>
          <div class="login-select-role-group" v-else>
            <div class="select-role-item select-active-item">管理员</div>
          </div>
          <div style="width: 85%; margin-top: 20px;">
            <el-form label-position="top" label-width="auto" :model="formLogin">
              <el-form-item label="用户名">
                <el-input v-model="formLogin.username" size="large">
                  <template #prefix>
                    <UserRound style="width: 16px"/>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item label="密码">
                <el-input v-model="formLogin.password" show-password size="large">
                  <template #prefix>
                    <LockKeyhole style="width: 16px"/>
                  </template>
                </el-input>
              </el-form-item>
              <el-form-item v-if="!isAdministrator">
                <el-checkbox v-model="formLogin.rememberPass">记住密码</el-checkbox>
              </el-form-item>
            </el-form>
            <el-button type="primary" style="width: 100%;margin-top: 15px;" size="large" @click="handleLogin">
              <LogIn class="common-btn-icon-style"/>
              登 录
            </el-button>
          </div>
        </div>
        <div class="login-right-common login-right-end"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { router } from '../../router'
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { UserLogin } from "../../api/index.ts";
import { LockKeyhole, UserRound, LogIn } from 'lucide-vue-next';
import {setCookie} from "../../utils/cookie.ts";

// 从当前路由获取是否为管理员登录标志
const isAdministrator = router.currentRoute.value.query?.admin

// 登录信息Form表单
const formLogin = reactive({
  username: '',
  password: '',
  rememberPass: false,
  isAdmin: false,  // 标志是否为管理员
})

const loginRole = ref('Student')

// 处理记住密码时的数据回写
const handleRemember = () => {
  if (!isAdministrator) {
    formLogin.isAdmin = false
    const { ROLE, LOGIN_INFO } = localStorage; // 解构出 localStorage 对象中的 ROLE 和 LOGIN_INFO 属性
    if (ROLE && LOGIN_INFO) { // 如果 ROLE 和 LOGIN_INFO 存在
      const role = ROLE; // 读取 ROLE
      const loginInfo = JSON.parse(LOGIN_INFO); // 解析 LOGIN_INFO 字符串为对象
      if (role === 'Student') {
        handleActiveStudent();
      } else {
        handleActiveTeacher();
      }
      Object.assign(formLogin, loginInfo); // 将解析后的登录信息合并到 formLogin 对象中
    }
  } else {
    loginRole.value = 'Admin';
    formLogin.isAdmin = true
  }
};

onMounted(() => {
  handleRemember()
})

// 处理激活的登录角色
const handleActiveRole = (index: any) => {
  if (!isAdministrator) {
    const roleItems = document.getElementsByClassName('select-role-item');
    const activeItemClass = 'select-active-item';
    // 添加 select-active-item 类到指定索引的元素
    roleItems[index].classList.add(activeItemClass);
    // 移除 select-active-item 类从另一个元素
    const otherIndex = index === 0 ? 1 : 0;
    roleItems[otherIndex].classList.remove(activeItemClass);
  }
};

// 处理学生角色
const handleActiveStudent = () => {
  handleActiveRole(0); // 角色类型索引为 0 表示学生
  loginRole.value = 'Student'
};

// 处理老师角色
const handleActiveTeacher = () => {
  handleActiveRole(1); // 角色类型索引为 1 表示老师
  loginRole.value = 'Teacher'
};

// 处理登录
const handleLogin = () => {
  // 根据用户选择的角色确定调用的登录函数
  const loginFunction = loginRole.value === 'Student' ? UserLogin.studentLoginApi : UserLogin.teacherLoginApi;

  // 调用相应的登录函数
  loginFunction(formLogin).then(response => {
    // 如果返回的响应状态码不是200，则显示错误信息并结束函数
    if (response.code !== 200) {
      ElMessage.error(response.msg);
      return;
    }
    // 显示登录成功的消息
    ElMessage.success('登录成功');
    // 存储Access Token
    localStorage.setItem('TOKEN', response.data['access'])
    // 存储角色信息
    localStorage.setItem('ROLE', loginRole.value);
    // 存储登录信息（登录人的姓名）
    const userInfo = { userId: response.data['userId'], username: response.data['name'] }
    setCookie('UserInfo', JSON.stringify(userInfo))
    // 如果用户选择了记住密码，则将登录信息存储到localStorage中，否则清除localStorage中的登录信息
    if (formLogin.rememberPass) {
      localStorage.setItem('LOGIN_INFO', JSON.stringify(formLogin));
    } else {
      localStorage.removeItem('LOGIN_INFO');
    }
    router.replace('/homepage')
  });
};

</script>

<style scoped lang="scss">
@import "../../style.scss";

.login-main-box {
  width: 100%;
  height: 100vh;
  display: flex;
}

.login-left-box {
  flex: 1;
  background: linear-gradient(135deg, #1a3a6b 0%, #2d5fa1 40%, #3a7bd5 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;

  &::before {
    content: "";
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 70%, rgba(255,255,255,0.06) 0%, transparent 50%),
                radial-gradient(circle at 70% 30%, rgba(255,255,255,0.04) 0%, transparent 50%);
    pointer-events: none;
  }

  .left-content {
    position: relative;
    z-index: 1;
    color: #fff;
    padding: 0 60px;
    max-width: 500px;

    .left-title {
      font-size: 36px;
      font-weight: bold;
      letter-spacing: 4px;
      margin-bottom: 16px;
    }

    .left-subtitle {
      font-size: 18px;
      opacity: 0.85;
      letter-spacing: 2px;
      margin-bottom: 40px;
    }

    .left-features {
      list-style: none;
      padding: 0;
      margin: 0;

      li {
        font-size: 16px;
        line-height: 2.4;
        opacity: 0.9;
        letter-spacing: 1px;
        padding-left: 24px;
        position: relative;

        &::before {
          content: "✓";
          position: absolute;
          left: 0;
          color: #7ec8f8;
          font-weight: bold;
        }
      }
    }
  }
}

.login-right-box {
  width: 480px;
  min-width: 420px;
  flex: 0 0 auto;
  background-color: #fff;
  display: flex;
  flex-direction: column;
  padding: 0 50px;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.08);

  .login-right-common {
    width: 100%;
  }
}

.login-right-logo-box {
  display: flex;
  flex: 2 1 auto;
  position: relative;
  flex-direction: column;

  &::before {
    height: 80px;
    display: block;
    content: "";
  }

  &::after {
    flex: 2 1 auto;
    display: block;
    content: "";
  }

  .logo-content {
    display: flex;
    align-items: center;

    .logo-wording-item {
      font-size: 22px;
      color: #1a3a6b;
      letter-spacing: 3px;
      font-weight: bold;
    }
  }
}

.login-right-form-box {
  height: 550px;
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  align-items: center;

  .form-title-wording {
    font-size: 18px;
    color: #2d5fa1;
    letter-spacing: 3px;
    font-weight: bolder;
  }

  .login-select-role-group {
    display: flex;
    margin-top: 28px;
    letter-spacing: 3px;

    .select-role-item {
      color: #3E3E3E;
      font-size: 18px;
      padding: 0 18px 8px 18px;
      position: relative;
      cursor: pointer;
    }
  }
}

.login-right-end {
  flex: 3 1 auto;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.select-active-item {
  &::after {
    position: absolute;
    content: "";
    width: 50px;
    height: 3px;
    background: #3a7bd5;
    left: calc(50% - 27px);
    bottom: 0;
    border-radius: 4px;
  }
}
</style>
