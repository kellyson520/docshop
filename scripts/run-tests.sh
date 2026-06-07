#!/bin/bash

/**
 * 测试运行脚本
 * 用于运行前端、后端和E2E测试
 */

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
测试运行脚本

用法: ./run-tests.sh [选项] [测试类型]

选项:
    -h, --help          显示帮助信息
    -v, --verbose       显示详细输出
    -c, --coverage      生成覆盖率报告
    -w, --watch         监听模式运行测试

测试类型:
    frontend            运行前端单元测试
    backend             运行后端单元测试
    e2e                 运行端到端测试
    integration         运行集成测试
    performance         运行性能测试
    security            运行安全测试
    all                 运行所有测试

示例:
    ./run-tests.sh frontend              # 运行前端测试
    ./run-tests.sh backend --coverage    # 运行后端测试并生成覆盖率报告
    ./run-tests.sh all                   # 运行所有测试
    ./run-tests.sh e2e --verbose         # 详细模式运行E2E测试
EOF
}

# 运行前端测试
run_frontend_tests() {
    print_info "运行前端单元测试..."
    cd /workspace/docdist/frontend
    
    if [ "$COVERAGE" = true ]; then
        npm run test:coverage
    elif [ "$WATCH" = true ]; then
        npm run test
    else
        npm run test -- --run
    fi
    
    if [ $? -eq 0 ]; then
        print_success "前端测试通过"
    else
        print_error "前端测试失败"
        exit 1
    fi
}

# 运行后端测试
run_backend_tests() {
    print_info "运行后端单元测试..."
    cd /workspace/docdist/backend
    
    if [ "$COVERAGE" = true ]; then
        python -m pytest tests/unit -v --cov=app --cov-report=html:../artifacts/coverage/backend-htmlcov --cov-report=term
    else
        python -m pytest tests/unit -v
    fi
    
    if [ $? -eq 0 ]; then
        print_success "后端单元测试通过"
    else
        print_error "后端单元测试失败"
        exit 1
    fi
}

# 运行集成测试
run_integration_tests() {
    print_info "运行集成测试..."
    cd /workspace/docdist/backend
    
    python -m pytest tests/integration -v
    
    if [ $? -eq 0 ]; then
        print_success "集成测试通过"
    else
        print_error "集成测试失败"
        exit 1
    fi
}

# 运行E2E测试
run_e2e_tests() {
    print_info "运行端到端测试..."
    cd /workspace/docdist/frontend
    
    # 确保已安装 Playwright 浏览器
    npx playwright install chromium
    
    if [ "$VERBOSE" = true ]; then
        npx playwright test --headed
    else
        npx playwright test
    fi
    
    if [ $? -eq 0 ]; then
        print_success "E2E测试通过"
    else
        print_error "E2E测试失败"
        exit 1
    fi
}

# 运行性能测试
run_performance_tests() {
    print_info "运行性能测试..."
    cd /workspace/docdist/backend
    
    print_info "运行基准测试..."
    python -m pytest tests/performance/test_benchmark.py -v --benchmark-only
    
    print_info "运行内存测试..."
    python -m pytest tests/performance/test_memory.py -v
    
    print_success "性能测试完成"
}

# 运行安全测试
run_security_tests() {
    print_info "运行安全测试..."
    cd /workspace/docdist/backend
    
    python -m pytest tests/security -v
    
    if [ $? -eq 0 ]; then
        print_success "安全测试通过"
    else
        print_error "安全测试失败"
        exit 1
    fi
}

# 运行所有测试
run_all_tests() {
    print_info "运行所有测试..."
    
    run_frontend_tests
    run_backend_tests
    run_integration_tests
    run_e2e_tests
    run_security_tests
    
    print_success "所有测试通过!"
}

# 解析命令行参数
VERBOSE=false
COVERAGE=false
WATCH=false
TEST_TYPE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -w|--watch)
            WATCH=true
            shift
            ;;
        frontend|backend|e2e|integration|performance|security|all)
            TEST_TYPE=$1
            shift
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 如果没有指定测试类型，显示帮助
if [ -z "$TEST_TYPE" ]; then
    show_help
    exit 0
fi

# 根据测试类型运行相应的测试
case $TEST_TYPE in
    frontend)
        run_frontend_tests
        ;;
    backend)
        run_backend_tests
        ;;
    e2e)
        run_e2e_tests
        ;;
    integration)
        run_integration_tests
        ;;
    performance)
        run_performance_tests
        ;;
    security)
        run_security_tests
        ;;
    all)
        run_all_tests
        ;;
    *)
        print_error "未知测试类型: $TEST_TYPE"
        show_help
        exit 1
        ;;
esac
