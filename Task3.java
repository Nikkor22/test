public class Task3 {
    public static void main(String[] args) {
        // 1. Создание массива с инициализацией
        int[] numbers = {7, 0, 117, 432, 31};

        // 2. Переменные для суммы и среднего
        int sum = 0;

        // 3. Улучшенный for для подсчёта суммы
        for (int num : numbers) {
            sum += num;
        }

        // 4. Среднее арифметическое
        double average = (double) sum / numbers.length;

        // 5. Вывод результата
        System.out.println("Сумма элементов массива = " + sum);
        System.out.println("Среднее арифметическое = " + average);
    }
}
