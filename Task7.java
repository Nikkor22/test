import java.util.Scanner;

public class Task7 {
    // Метод для вычисления факториала числа n
    public static long factorial(int n) {
        long result = 1;
        for (int i = 1; i <= n; i++) {
            result *= i; // умножаем результат на i
        }
        return result;
    }

    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

        // Ввод числа пользователем
        System.out.print("Введите число для вычисления факториала: ");
        int n = sc.nextInt();

        // Проверка на дебила — факториал определён только для n >= 0
        if (n < 0) {
            System.out.println("Ошибка: факториал определён только для неотрицательных чисел!");
            return;
        }

        // Вызов метода
        long fact = factorial(n);

        // Вывод результата
        System.out.println("Факториал числа " + n + " равен " + fact);
    }
}
