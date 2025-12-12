import java.util.Scanner;

public class Task4 {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

        // --- Ввод массива ---
        System.out.print("Введите размер массива: ");
        int n;
        while (true) { // проверка на корректный ввод размера
            if (sc.hasNextInt()) {
                n = sc.nextInt();
                if (n > 0) break;
                else System.out.print("Размер массива должен быть > 0. Введите снова: ");
            } else {
                System.out.print("Ошибка: введите целое число: ");
                sc.next(); // пропускаем неверный ввод
            }
        }

        int[] numbers = new int[n];
        System.out.println("Введите " + n + " целых чисел:");
        for (int i = 0; i < n; i++) {
            while (!sc.hasNextInt()) {
                System.out.print("Ошибка: введите целое число: ");
                sc.next();
            }
            numbers[i] = sc.nextInt();
        }

        // --- Сумма через while ---
        int sumWhile = 0;
        int i = 0;
        while (i < numbers.length) {
            sumWhile += numbers[i];
            i++;
        }

        // --- Сумма через do while ---
        int sumDoWhile = 0;
        int j = 0;
        if (numbers.length > 0) {
            do {
                sumDoWhile += numbers[j];
                j++;
            } while (j < numbers.length);
        }

        // --- Поиск min и max ---
        int min = numbers[0];
        int max = numbers[0];
        for (int num : numbers) {
            if (num < min) min = num;
            if (num > max) max = num;
        }

        // --- Вывод результата ---
        System.out.println("Сумма = " + sumWhile);
        System.out.println("Сумма = " + sumDoWhile);
        System.out.println("Минимальный элемент = " + min);
        System.out.println("Максимальный элемент = " + max);
    }
}
